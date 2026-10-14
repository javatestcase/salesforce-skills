#!/usr/bin/env python3
"""
LLM-as-judge tier: grade a skill's output against its eval.yaml rubric.

Two kinds of checks per output:
  1. Deterministic  — output_must_contain, record links, no raw __c API names,
                      no unresolved template tokens. Free, no model.
  2. LLM rubric     — each rubric criterion graded in its OWN model call (isolation
                      avoids one verdict coloring another), with the evidence the skill
                      had, so grounding criteria can be checked value by value.
                      Verdict per criterion: PASS / FAIL / N/A, plus rationale + quote.

The judge never sees how the output was produced — only the skill's instructions, the
evidence, and the output.

Usage:
    # grade one output (evidence defaults to <output>.evidence.json next to it)
    python3 evals/judge.py --skill daily-briefing --output evals/outputs/daily-briefing/live.md

    # prove the judge catches planted defects (fixtures in evals/calibration/<skill>/)
    python3 evals/judge.py --calibrate evals/calibration/daily-briefing

    # inspect the prompt without calling a model
    python3 evals/judge.py --skill daily-briefing --output X.md --print-prompt

Options: --samples N (majority vote over N calls, default 1), --model, --profile,
         --region, --workers N, --json, --response-file F (canned model reply; offline).

Exit codes: 0 = PASS, 1 = FAIL (or calibration disagreement), 2 = error/config.
"""

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(EVALS_DIR)
SKILLS_DIR = os.path.join(PLUGIN_ROOT, "skills")          # shipped: SKILL.md only
EVAL_SKILLS_DIR = os.path.join(EVALS_DIR, "skills")       # eval-only: eval.yaml, reads/
sys.path.insert(0, EVALS_DIR)

import llm  # noqa: E402

VERDICTS = ("PASS", "FAIL", "N/A")

JUDGE_SYSTEM = """You are a strict, impartial evaluator of an AI sales assistant's output.
You grade exactly ONE criterion per request. You did not write the output and have no stake
in it. Judge only what is on the page, against the evidence provided. The evidence is ground
truth: it is the complete data the assistant had. Do not assume facts that are not in it."""

JUDGE_INSTRUCTIONS = """## How to grade
Grade ONLY the criterion above. Each other rule is graded in a separate request by someone
else. If you notice a problem that belongs to a different rule, put it in "out_of_scope" and do
NOT let it affect this verdict, however serious it is.

What common criterion types mean:
- Grounding / fabrication ("traceable", "fabricated", "invented", "cite"): a violation is an
  output value (number, name, date, stage, meeting, status) that contradicts the evidence or has
  no source in it. A value is sourced if it appears in ANY read in the evidence; it does not
  have to come from the read whose name matches the output section. Derived values (sums, day
  counts, weekdays, timezone conversions) are fine only if they compute correctly — check every
  stated count and total against the Computed facts, not by adding numbers yourself. Formatting
  differences ($329,000 vs 329000, date formats) are NOT violations. Showing a raw field name
  or record Id next to a correct value is NOT a grounding violation.
- Blank handling ("blank"): a violation is a field that is null/empty in the evidence shown with
  a non-blank value. Displaying it as BLANK, blank, "—", "not set", or a warning marker is the
  CORRECT behavior. A wrong non-null value is a grounding issue, not a blank-handling issue.
- Labeling ("labels", "API names", "Ids"): a violation is an API field name (StageName,
  NextStep, Foo__c) or a raw record Id shown to the user outside a record link. Record Ids inside
  record-link URLs are expected. Wrong values are NOT labeling violations.
- Anything else: judge the plain meaning of the criterion.

Other rules:
- N/A: the criterion's precondition does not apply (for example, it describes behavior for an
  empty result and the result was not empty).
- A section the skill says to omit or mark unavailable when its connector/data is missing may be
  absent or noted as unavailable.
- Every violation needs a quote copied VERBATIM from the output. If you cannot quote it, it is
  not a violation.
- Do not reward length, tone, or polish.

Respond with ONLY a JSON object, no other text:
{"checked": "<one sentence: what you compared>",
 "violations": [{"quote": "<verbatim output text>", "why": "<how it violates THIS criterion>",
                 "in_scope": true | false}],
 "out_of_scope": ["<problems that belong to other criteria>"],
 "verdict": "PASS" | "FAIL" | "N/A"}
For each violation, set "in_scope" to false if, applying the definitions above, the problem
really belongs to a different rule. Items with in_scope false do not count.
verdict must be FAIL if and only if there is at least one violation with in_scope true."""


# ---------------------------------------------------------------- eval.yaml parsing

def _parse_value(s):
    s = s.strip()
    if s.startswith('"'):
        i = 1
        while i < len(s):
            if s[i] == "\\":
                i += 2
                continue
            if s[i] == '"':
                break
            i += 1
        try:
            return json.loads(s[: i + 1])
        except json.JSONDecodeError:
            return s[1:i]
    if s.startswith("'"):
        j = s.find("'", 1)
        return s[1:j] if j != -1 else s[1:]
    s = s.split(" #", 1)[0].strip()
    if s.startswith("["):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return s
    if s in ("true", "false"):
        return s == "true"
    try:
        return int(s)
    except ValueError:
        return s


def load_spec(skill):
    """Read the TOP-LEVEL keys of evals/skills/<skill>/eval.yaml (scalars and simple string lists).

    Nested blocks (safety:, email_eval:) are not needed by the judge; their nested lists
    (e.g. email_eval.rubric, indented 4 spaces) are deliberately not picked up.
    """
    path = os.path.join(EVAL_SKILLS_DIR, skill, "eval.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no eval.yaml for skill {skill!r} at {path}")
    spec, current = {}, None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            top = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
            if top:
                key, rest = top.groups()
                rest_clean = rest.split(" #", 1)[0].strip() if not rest.strip().startswith(('"', "'")) else rest
                if rest_clean == "":
                    spec[key], current = [], key
                else:
                    spec[key], current = _parse_value(rest), None
                continue
            item = re.match(r"^  - (.*)$", line)  # exactly one indent level = top-level list
            if item and current is not None and isinstance(spec.get(current), list):
                spec[current].append(_parse_value(item.group(1)))
    return spec


def read_skill_md(skill):
    with open(os.path.join(SKILLS_DIR, skill, "SKILL.md"), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- deterministic checks

LINK_RE = re.compile(r"https?://\S+?/lightning/r/[A-Za-z0-9_]+/[A-Za-z0-9]{15,18}/view")
RAW_API_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*__c\b")
TOKEN_RE = re.compile(r"\{\{|\}\}|<[A-Z][A-Z0-9_]{2,}>")


def deterministic_checks(spec, output):
    checks = []
    lower = output.lower()
    for needle in spec.get("output_must_contain") or []:
        ok = str(needle).lower() in lower
        checks.append({"check": f"contains {needle!r}", "ok": ok,
                       "detail": "" if ok else "missing"})
    if spec.get("output_must_link_records") is True:
        n = len(LINK_RE.findall(output))
        checks.append({"check": "links Salesforce records", "ok": n > 0,
                       "detail": f"{n} record link(s)"})
    raw = sorted(set(RAW_API_RE.findall(LINK_RE.sub("", output))))
    checks.append({"check": "no raw __c API names", "ok": not raw,
                   "detail": ", ".join(raw)})
    tokens = sorted(set(TOKEN_RE.findall(output)))
    checks.append({"check": "no unresolved template tokens", "ok": not tokens,
                   "detail": ", ".join(tokens)})
    return checks


# ---------------------------------------------------------------- LLM criteria

def computed_facts(evidence):
    """Exact row counts and Amount sums per read, computed by code.

    Models are unreliable at summing long columns, so the judge gets these as facts to check
    stated counts/totals against. Given to the judge only, never to the executor.
    """
    facts = []
    for name, data in ((evidence or {}).get("reads") or {}).items():
        agg = data.get("uiapi", {}).get("aggregate") if isinstance(data, dict) else None
        if isinstance(agg, dict):
            for obj, v in agg.items():
                for e in (v or {}).get("edges") or []:
                    values = {}
                    for field, fns in ((e.get("node") or {}).get("aggregate") or {}).items():
                        for fn, res in (fns or {}).items():
                            if isinstance(res, dict):
                                values[f"{fn}({field})"] = res.get("value")
                                if res.get("displayValue") is not None:
                                    values[f"{fn}({field}).displayValue"] = res["displayValue"]
                    if values:
                        facts.append({"read": name, "object": obj, "aggregate": values,
                                      "note": "computed by Salesforce over ALL matching records"})
            continue
        q = data.get("uiapi", {}).get("query") if isinstance(data, dict) else None
        if not isinstance(q, dict):
            continue
        for obj, v in q.items():
            if not isinstance(v, dict) or not isinstance(v.get("edges"), list):
                continue
            nodes = [e.get("node", {}) for e in v["edges"] if isinstance(e, dict)]
            fact = {"read": name, "object": obj, "rows_in_evidence": len(nodes)}
            nums = [n["Amount"].get("value") for n in nodes if isinstance(n.get("Amount"), dict)]
            nums = [x for x in nums if isinstance(x, (int, float))]
            if nums:
                total = sum(nums)
                fact["sum_Amount"] = int(total) if float(total).is_integer() else total
                fact["rows_with_Amount"] = len(nums)
            facts.append(fact)
    for t in (evidence or {}).get("truncation") or []:
        facts.append({"read": t.get("read"), "rows_returned_by_org": t.get("total_rows"),
                      "rows_in_evidence": t.get("rows_shown"),
                      "note": "sum_Amount above covers only the rows in evidence"})
    return facts


def build_judge_prompt(skill, skill_md, evidence, output, criterion):
    evidence_text = json.dumps(evidence, indent=1, ensure_ascii=False) if evidence else "(none provided)"
    facts = computed_facts(evidence)
    facts_text = (
        "## Computed facts (exact — computed by code from the evidence above)\n"
        "Use these to check any count or total stated in the output. Two kinds: row facts\n"
        "(count/sum of the rows present in the evidence) and aggregate facts (computed by\n"
        "Salesforce over ALL matching records, which can exceed the rows shown). A stated count\n"
        "or total is correct if it matches the aggregate fact for that section, or the row fact\n"
        "when the section has no aggregate. If an aggregate exists for a section and the stated\n"
        "count or total differs from it, that is a grounding violation, even if it matches the\n"
        "visible rows.\n"
        f"```json\n{json.dumps(facts, indent=1)}\n```\n\n"
    ) if facts else ""
    user = (
        f"## Skill: {skill}\n\n"
        "## Skill instructions (what the output was supposed to do)\n"
        f"<<<SKILL\n{skill_md}\nSKILL>>>\n\n"
        "## Evidence (ground truth — the data the assistant had)\n"
        f"```json\n{evidence_text}\n```\n\n"
        f"{facts_text}"
        "## Output under evaluation\n"
        f"<<<OUTPUT\n{output}\nOUTPUT>>>\n\n"
        f"## Criterion\n\"{criterion}\"\n\n"
        f"{JUDGE_INSTRUCTIONS}"
    )
    return JUDGE_SYSTEM, user


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _quote_in_output(quote, output_norm):
    q = _norm(quote).strip("\"'…. ")
    return bool(q) and (q in output_norm or q[:60] in output_norm)


def parse_verdict(text, output=None):
    """Extract a verdict from a model reply. verdict=ERROR if unparseable.

    Current reply format: {checked, violations:[{quote, why}], out_of_scope, verdict}.
    The contract "FAIL iff violations" is enforced here, and when `output` is given, any
    violation whose quote does not appear in the output is dropped as unverifiable.
    The older {verdict, rationale, quote} format is still accepted.
    """
    candidate = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    start, end = candidate.find("{"), candidate.rfind("}")
    obj = None
    if start != -1 and end > start:
        try:
            obj = json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            obj = None
    if not isinstance(obj, dict):
        return {"verdict": "ERROR", "rationale": f"unparseable judge reply: {(text or '')[:200]}",
                "quote": "", "out_of_scope": []}

    verdict = str(obj.get("verdict", "")).strip().upper()
    verdict = "N/A" if verdict in ("NA", "N/A", "NOT APPLICABLE") else verdict

    violations = obj.get("violations")
    if isinstance(violations, list):
        vs = [v for v in violations if isinstance(v, dict)]
        extra_oos = [str(v.get("why", "")) for v in vs if v.get("in_scope") is False]
        vs = [v for v in vs if v.get("in_scope") is not False]
        dropped = 0
        if output is not None:
            out_n = _norm(output)
            kept = [v for v in vs if _quote_in_output(str(v.get("quote", "")), out_n)]
            dropped, vs = len(vs) - len(kept), kept
        if vs:
            verdict = "FAIL"
        elif verdict == "FAIL":
            verdict = "PASS"  # a FAIL with no verifiable violation does not stand
        if verdict not in VERDICTS:
            return {"verdict": "ERROR", "rationale": f"bad verdict {verdict!r}", "quote": "",
                    "out_of_scope": []}
        rationale = str(vs[0].get("why", "")) if vs else str(obj.get("checked", ""))
        if dropped:
            rationale += f" [{dropped} unverifiable violation(s) dropped]"
        return {"verdict": verdict, "rationale": rationale.strip(),
                "quote": str(vs[0].get("quote", "")).strip() if vs else "",
                "out_of_scope": [str(x) for x in obj.get("out_of_scope") or []] + extra_oos}

    if verdict in VERDICTS:
        return {"verdict": verdict, "rationale": str(obj.get("rationale", "")).strip(),
                "quote": str(obj.get("quote", "")).strip(), "out_of_scope": []}
    return {"verdict": "ERROR", "rationale": f"unparseable judge reply: {(text or '')[:200]}",
            "quote": "", "out_of_scope": []}


def majority(votes):
    """Majority verdict. Ties break toward the stricter outcome: FAIL > PASS > N/A.
    ERROR votes are ignored unless every vote is an ERROR."""
    real = [v for v in votes if v in VERDICTS]
    if not real:
        return "ERROR"
    counts = {v: real.count(v) for v in VERDICTS}
    top = max(counts.values())
    for v in ("FAIL", "PASS", "N/A"):
        if counts[v] == top:
            return v


def make_model_call(model=None, profile=None, region=None, response_file=None):
    """Return call_fn(system, user, temperature) -> reply text."""
    if response_file:
        with open(response_file, encoding="utf-8") as f:
            canned = f.read()
        return lambda system, user, temperature: canned

    def call(system, user, temperature):
        text, _ = llm.converse(system, user, model=model, profile=profile, region=region,
                               max_tokens=1000, temperature=temperature)
        return text
    return call


def evaluate(skill, output, evidence, call_fn, samples=1, workers=4):
    """Grade one output. Returns a report dict with checks, criteria, and overall."""
    spec = load_spec(skill)
    skill_md = read_skill_md(skill)
    rubric = [c for c in (spec.get("rubric") or []) if isinstance(c, str)]
    checks = deterministic_checks(spec, output)
    temperature = 0.0 if samples == 1 else 0.5

    jobs = []
    for idx, criterion in enumerate(rubric):
        system, user = build_judge_prompt(skill, skill_md, evidence, output, criterion)
        for _ in range(samples):
            jobs.append((idx, system, user))

    def run(job):
        idx, system, user = job
        try:
            return idx, parse_verdict(call_fn(system, user, temperature), output)
        except llm.LLMError as e:
            return idx, {"verdict": "ERROR", "rationale": str(e), "quote": "", "out_of_scope": []}

    results = {i: [] for i in range(len(rubric))}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for idx, verdict in pool.map(run, jobs):
            results[idx].append(verdict)

    criteria = []
    for idx, criterion in enumerate(rubric):
        votes = results[idx]
        final = majority([v["verdict"] for v in votes])
        chosen = next((v for v in votes if v["verdict"] == final), votes[0] if votes else {})
        criteria.append({"criterion": criterion, "verdict": final,
                         "votes": [v["verdict"] for v in votes],
                         "rationale": chosen.get("rationale", ""),
                         "quote": chosen.get("quote", ""),
                         "out_of_scope": chosen.get("out_of_scope", [])})

    if any(not c["ok"] for c in checks) or any(c["verdict"] == "FAIL" for c in criteria):
        overall = "FAIL"
    elif any(c["verdict"] == "ERROR" for c in criteria):
        overall = "ERROR"
    else:
        overall = "PASS"
    return {"skill": skill, "overall": overall, "checks": checks, "criteria": criteria}


# ---------------------------------------------------------------- calibration

def calibrate(cal_dir, call_fn, samples=1, workers=4):
    """Run every case in a calibration dir and compare to expected.json.

    expected.json: {"skill": "<name>", "cases": {"<case>": {"overall": "PASS"|"FAIL",
                    "must_fail": [criterion substrings], "must_pass": [criterion substrings],
                    "must_fail_checks": [check substrings]}}}
    must_pass catches scope bleed: a judge failing a criterion for another criterion's defect.
    Each case is <case>.md. Evidence: the case's "evidence" key if set, else <case>.evidence.json,
    else the shared evidence.json.
    """
    with open(os.path.join(cal_dir, "expected.json"), encoding="utf-8") as f:
        expected = json.load(f)
    skill = expected["skill"]
    shared_ev = os.path.join(cal_dir, "evidence.json")
    outcomes = []
    for case, exp in expected["cases"].items():
        with open(os.path.join(cal_dir, f"{case}.md"), encoding="utf-8") as f:
            output = f.read()
        if exp.get("evidence"):
            ev_path = os.path.join(cal_dir, exp["evidence"])
        else:
            ev_path = os.path.join(cal_dir, f"{case}.evidence.json")
            ev_path = ev_path if os.path.exists(ev_path) else shared_ev
        with open(ev_path, encoding="utf-8") as f:
            evidence = json.load(f)
        report = evaluate(skill, output, evidence, call_fn, samples=samples, workers=workers)

        problems = []
        if report["overall"] != exp["overall"]:
            problems.append(f"overall {report['overall']} (expected {exp['overall']})")
        for sub in exp.get("must_fail", []):
            hit = [c for c in report["criteria"] if sub.lower() in c["criterion"].lower()]
            if not hit or all(c["verdict"] != "FAIL" for c in hit):
                problems.append(f"criterion matching {sub!r} was not FAIL")
        for sub in exp.get("must_pass", []):
            hit = [c for c in report["criteria"] if sub.lower() in c["criterion"].lower()]
            if not hit or any(c["verdict"] in ("FAIL", "ERROR") for c in hit):
                problems.append(f"criterion matching {sub!r} was FAIL (should be PASS or N/A)")
        for sub in exp.get("must_fail_checks", []):
            hit = [c for c in report["checks"] if sub.lower() in c["check"].lower()]
            if not hit or all(c["ok"] for c in hit):
                problems.append(f"check matching {sub!r} did not fail")
        outcomes.append({"case": case, "agrees": not problems, "problems": problems, "report": report})
    return {"skill": skill, "outcomes": outcomes,
            "agreement": sum(o["agrees"] for o in outcomes), "total": len(outcomes)}


# ---------------------------------------------------------------- output

def print_report(report, indent=""):
    print(f"{indent}[{report['overall']}] {report['skill']}")
    for c in report["checks"]:
        if not c["ok"]:
            print(f"{indent}   x check: {c['check']} — {c['detail']}")
    for c in report["criteria"]:
        mark = {"PASS": "ok ", "FAIL": "x  ", "N/A": "n/a", "ERROR": "ERR"}[c["verdict"]]
        votes = f" votes={c['votes']}" if len(c["votes"]) > 1 else ""
        print(f"{indent}   [{mark}] {c['criterion']}{votes}")
        if c["verdict"] in ("FAIL", "ERROR"):
            print(f"{indent}         why: {c['rationale']}")
            if c["quote"]:
                print(f"{indent}         quote: {c['quote'][:160]}")


def _arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def main(argv):
    samples = int(_arg(argv, "--samples", "1"))
    workers = int(_arg(argv, "--workers", "4"))
    model, profile, region = _arg(argv, "--model"), _arg(argv, "--profile"), _arg(argv, "--region")
    response_file = _arg(argv, "--response-file")
    as_json = "--json" in argv

    try:
        if not response_file:
            llm.check_profile(profile or llm.DEFAULT_PROFILE)
        call_fn = make_model_call(model, profile, region, response_file)

        cal_dir = _arg(argv, "--calibrate")
        if cal_dir:
            result = calibrate(cal_dir, call_fn, samples=samples, workers=workers)
            if as_json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Judge calibration — {result['skill']}  (model: {model or llm.DEFAULT_MODEL})")
                for o in result["outcomes"]:
                    print(f"\n  case {o['case']}: {'AGREES' if o['agrees'] else 'DISAGREES'}")
                    for p in o["problems"]:
                        print(f"    ! {p}")
                    print_report(o["report"], indent="    ")
                print(f"\nAgreement: {result['agreement']}/{result['total']}")
            return 0 if result["agreement"] == result["total"] else 1

        skill, output_path = _arg(argv, "--skill"), _arg(argv, "--output")
        if not skill or not output_path:
            print("error: need --skill and --output, or --calibrate <dir>")
            return 2
        with open(output_path, encoding="utf-8") as f:
            output = f.read()
        ev_path = _arg(argv, "--evidence") or re.sub(r"\.md$", "", output_path) + ".evidence.json"
        evidence = None
        if os.path.exists(ev_path):
            with open(ev_path, encoding="utf-8") as f:
                evidence = json.load(f)

        if "--print-prompt" in argv:
            spec = load_spec(skill)
            rubric = spec.get("rubric") or []
            system, user = build_judge_prompt(skill, read_skill_md(skill), evidence, output,
                                              rubric[0] if rubric else "(no rubric)")
            print(f"=== SYSTEM ===\n{system}\n\n=== USER (criterion 1 of {len(rubric)}) ===\n{user}")
            return 0

        report = evaluate(skill, output, evidence, call_fn, samples=samples, workers=workers)
        if as_json:
            print(json.dumps(report, indent=2))
        else:
            if evidence is None:
                print("warning: no evidence file — grounding criteria cannot be verified")
            print_report(report)
        return {"PASS": 0, "FAIL": 1}.get(report["overall"], 2)
    except (llm.LLMError, FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
