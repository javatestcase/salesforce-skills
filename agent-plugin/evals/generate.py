#!/usr/bin/env python3
"""
Offline executor: produce a skill's output from live org reads, for the judge to grade.

This stands in for the agent host (Quick) when no host is available:
  1. Runs the skill's evals/skills/<name>/reads/*.graphql against an org (READ-ONLY, via
     run_reads.fetch_graphql).
  2. Bundles the results as an evidence file (HTML entities unescaped, large edge lists capped).
  3. Gives the model the skill's SKILL.md + the evidence + a user request, and asks for the
     skill's final deliverable. The executor NEVER sees the rubric or eval.yaml criteria.

Outputs (git-ignored):
    evals/outputs/<skill>/<case>.md             the generated deliverable
    evals/outputs/<skill>/<case>.evidence.json  exactly what the executor saw (judge input)

Usage:
    python3 evals/generate.py --skill daily-briefing --org genwatt-demo
    python3 evals/generate.py --skill call-prep --org genwatt-demo --prompt "prep me for my next call"
    python3 evals/generate.py --skill daily-briefing --evidence path/to/evidence.json --case fixture
    python3 evals/generate.py --skill daily-briefing --org genwatt-demo --print-prompt   # no model call

Then grade:
    python3 evals/judge.py --skill daily-briefing --output evals/outputs/daily-briefing/live.md

Limits: this is not the Quick runtime. It exercises SKILL.md instructions + real data ->
deliverable. It does not test trigger/routing, and non-Salesforce connectors (email, docs,
Slack, web) are reported to the executor as unavailable.
"""

import datetime
import html
import json
import os
import subprocess
import sys

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(EVALS_DIR)
EVAL_SKILLS_DIR = os.path.join(EVALS_DIR, "skills")   # eval-only: eval.yaml, reads/
OUTPUTS_DIR = os.path.join(EVALS_DIR, "outputs")
sys.path.insert(0, EVALS_DIR)

import llm  # noqa: E402
from judge import load_spec, read_skill_md  # noqa: E402
from run_reads import fetch_graphql  # noqa: E402

EXECUTOR_SYSTEM = """You are a Salesforce sales assistant running inside an agent host. A skill
has been activated for the user's request. Follow the skill's instructions exactly to produce its
final deliverable.

In this run the host has ALREADY executed the skill's Salesforce reads; their results are provided
below as the query results. You cannot call any tools. The reads may differ slightly from the
skill's templated queries (for example, no per-user scope filter); treat the provided results as
what the queries returned. Connectors other than Salesforce (email, docs, Slack, web, and any
calendar other than Salesforce Events) are UNAVAILABLE in this run — follow the skill's
instructions for missing optional context. Never invent data that is not in the results.

Output ONLY the final deliverable in Markdown. No preamble, no explanation of your process."""

CONNECTORS = {
    "salesforce": "available (reads pre-executed by the host, results below)",
    "email": "unavailable",
    "docs": "unavailable",
    "slack": "unavailable",
    "web": "unavailable",
    "calendar": "unavailable except Salesforce Event records",
}


def org_instance_url(org):
    """Instance URL for record links (read-only `sf org display`)."""
    try:
        proc = subprocess.run(["sf", "org", "display", "--target-org", org, "--json"],
                              capture_output=True, text=True, timeout=60)
        out = proc.stdout
        data = json.loads(out[out.find("{"):])
        return data.get("result", {}).get("instanceUrl")
    except (subprocess.SubprocessError, ValueError, json.JSONDecodeError, FileNotFoundError):
        return None


def unescape(obj):
    """The CLI returns HTML-escaped strings (&amp;, &#39;). Restore them recursively."""
    if isinstance(obj, str):
        return html.unescape(obj)
    if isinstance(obj, list):
        return [unescape(x) for x in obj]
    if isinstance(obj, dict):
        return {k: unescape(v) for k, v in obj.items()}
    return obj


def cap_edges(obj, cap, read_name, notes, path="data"):
    """Truncate any edge list longer than cap, recording what was cut."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "edges" and isinstance(v, list) and len(v) > cap:
                notes.append({"read": read_name, "at": path, "total_rows": len(v), "rows_shown": cap})
                obj[k] = v[:cap]
            else:
                cap_edges(v, cap, read_name, notes, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            cap_edges(v, cap, read_name, notes, f"{path}[{i}]")


def build_evidence(skill, org, row_cap=25):
    reads_dir = os.path.join(EVAL_SKILLS_DIR, skill, "reads")
    reads, notes = {}, []
    if os.path.isdir(reads_dir):
        for fn in sorted(os.listdir(reads_dir)):
            if not fn.endswith(".graphql"):
                continue
            name = fn[: -len(".graphql")]
            ok, detail, data = fetch_graphql(org, os.path.join(reads_dir, fn))
            if not ok:
                reads[name] = {"error": detail}
                continue
            data = unescape(data)
            cap_edges(data, row_cap, name, notes)
            reads[name] = data
    return {
        "skill": skill,
        "org": org,
        "instanceUrl": org_instance_url(org),
        "today": datetime.date.today().isoformat(),
        "connectors": CONNECTORS,
        "truncation": notes,
        "reads": reads,
    }


def build_executor_prompt(skill_md, evidence, request):
    trunc = ""
    if evidence.get("truncation"):
        lines = [f"- {t['read']}: {t['total_rows']} rows returned, first {t['rows_shown']} shown"
                 for t in evidence["truncation"]]
        trunc = "\n## Truncation (rows the host did not pass through)\n" + "\n".join(lines) + "\n"
    reads = "\n\n".join(
        f"### {name}\n```json\n{json.dumps(data, indent=1, ensure_ascii=False)}\n```"
        for name, data in evidence.get("reads", {}).items()
    )
    user = (
        "## Skill instructions\n"
        f"<<<SKILL\n{skill_md}\nSKILL>>>\n\n"
        "## Org context\n"
        f"- instanceUrl: {evidence.get('instanceUrl') or '(unknown)'}\n"
        f"- today: {evidence.get('today')}\n"
        f"- connectors: {json.dumps(evidence.get('connectors', CONNECTORS))}\n"
        f"{trunc}\n"
        "## Salesforce read results (already executed by the host)\n"
        f"{reads or '(no reads)'}\n\n"
        "## User request\n"
        f"{request}\n"
    )
    return EXECUTOR_SYSTEM, user


def strip_outer_fence(text):
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if t.endswith("```") and first_nl != -1:
            return t[first_nl + 1:-3].strip()
    return t


def _arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def main(argv):
    skill = _arg(argv, "--skill")
    org = _arg(argv, "--org")
    evidence_in = _arg(argv, "--evidence")
    case = _arg(argv, "--case", "live")
    row_cap = int(_arg(argv, "--row-cap", "25"))
    model, profile, region = _arg(argv, "--model"), _arg(argv, "--profile"), _arg(argv, "--region")
    if not skill or not (org or evidence_in):
        print("error: need --skill and either --org <alias> or --evidence <file>")
        return 2

    try:
        spec = load_spec(skill)
        request = _arg(argv, "--prompt") or next(iter(spec.get("should_trigger") or []), "Run this skill.")
        skill_md = read_skill_md(skill)
        if evidence_in:
            with open(evidence_in, encoding="utf-8") as f:
                evidence = json.load(f)
        else:
            evidence = build_evidence(skill, org, row_cap=row_cap)
        evidence["request"] = request

        system, user = build_executor_prompt(skill_md, evidence, request)
        if "--print-prompt" in argv:
            print(f"=== SYSTEM ===\n{system}\n\n=== USER ===\n{user}")
            return 0

        llm.check_profile(profile or llm.DEFAULT_PROFILE)
        text, usage = llm.converse(system, user, model=model, profile=profile, region=region,
                                   max_tokens=4000, temperature=0.0)
        output = strip_outer_fence(text)

        out_dir = os.path.join(OUTPUTS_DIR, skill)
        os.makedirs(out_dir, exist_ok=True)
        out_md = os.path.join(out_dir, f"{case}.md")
        out_ev = os.path.join(out_dir, f"{case}.evidence.json")
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        with open(out_ev, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=1, ensure_ascii=False)

        failed = [n for n, d in evidence["reads"].items() if isinstance(d, dict) and "error" in d]
        print(f"wrote {os.path.relpath(out_md, PLUGIN_ROOT)}")
        print(f"wrote {os.path.relpath(out_ev, PLUGIN_ROOT)}")
        if failed:
            print(f"warning: reads failed and were passed as errors: {', '.join(failed)}")
        print(f"tokens: {usage.get('totalTokens', '?')}")
        print(f"grade:  python3 evals/judge.py --skill {skill} --output {os.path.relpath(out_md, PLUGIN_ROOT)}")
        return 0
    except (llm.LLMError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
