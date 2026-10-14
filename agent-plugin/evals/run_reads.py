#!/usr/bin/env python3
"""
Layer B (partial) — live read-connectivity eval runner.

For each skill, executes its `reads/*.graphql` fixtures against a connected Salesforce
org using the Salesforce CLI, and scores whether each read:
  1. reached the org and returned HTTP/GraphQL success,
  2. carried no GraphQL `errors`,
  3. returned at least one row (where a row set is expected).

READ-ONLY BY CONSTRUCTION. This runner only issues `sf api request graphql` (a read).
It never creates, updates, deletes, deploys, or sends anything. There is no code path
here that performs a write.

What this DOES exercise (CLI-only, no agent host):
  - The skill's GraphQL reads are valid against a real org schema and return data.
  - The portable query contract works end-to-end on live (synthetic) data.

What this does NOT exercise (needs the agent runtime — Quick/Claude):
  - Trigger/routing (did the skill activate for a prompt).
  - The assembled Markdown output and its rubric grading.
  - The email draft / never-send behavior (no email connector here).
These remain in eval.yaml as the host-run contract.

Fixtures live in evals/skills/<name>/reads/*.graphql, outside the shipped skill folders.

Usage:
    python3 evals/run_reads.py --org genwatt-demo
    python3 evals/run_reads.py --org genwatt-demo daily-briefing
    python3 evals/run_reads.py --org genwatt-demo --json
"""

import os
import sys
import json
import subprocess

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_SKILLS_DIR = os.path.join(PLUGIN_ROOT, "evals", "skills")


def fetch_graphql(org, path):
    """Run one .graphql fixture read-only via the Salesforce CLI.

    Returns (ok, detail, data) where data is the GraphQL `data` object on success.
    Reused by generate.py to build the evidence bundle from live reads.
    """
    try:
        proc = subprocess.run(
            ["sf", "api", "request", "graphql", "--body", path, "--target-org", org],
            capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError:
        return False, "sf CLI not found on PATH", None
    except subprocess.TimeoutExpired:
        return False, "timed out after 120s", None

    out = proc.stdout.strip()
    # The CLI prints a warning banner before the JSON; find the JSON object.
    brace = out.find("{")
    if brace == -1:
        return False, f"no JSON in response (exit {proc.returncode}): {out[:200]}", None
    try:
        payload = json.loads(out[brace:])
    except json.JSONDecodeError as e:
        return False, f"unparseable JSON: {e}", None

    errors = payload.get("errors") or []
    if errors:
        msgs = "; ".join(e.get("message", str(e)) for e in errors)
        return False, f"GraphQL errors: {msgs}", None

    return True, "ok", payload.get("data", {})


def aggregate_ok(data):
    """True if an aggregate read returned at least one aggregate value."""
    agg = (data or {}).get("uiapi", {}).get("aggregate")
    if not isinstance(agg, dict):
        return False
    for v in agg.values():
        for e in (v or {}).get("edges") or []:
            if (e.get("node") or {}).get("aggregate"):
                return True
    return False


def run_graphql(org, path):
    """Run one fixture and count rows. Returns (ok, detail, rows).

    detail is "aggregate" for uiapi.aggregate reads (no row set; checked for a value instead).
    """
    ok, detail, data = fetch_graphql(org, path)
    if not ok:
        return False, detail, None
    if isinstance((data or {}).get("uiapi", {}).get("aggregate"), dict):
        if not aggregate_ok(data):
            return False, "aggregate read returned no values", None
        return True, "aggregate", None
    return True, "ok", count_rows(data)


def count_rows(data):
    """Best-effort count of returned nodes across any query aliases in the response.

    Returns None for reads that legitimately have no edge sets (grounding-style):
    objectInfos metadata reads and currentUser reads. Those are marked "grounding"
    and are exempt from the row-count expectation.
    """
    uiapi = data.get("uiapi", {})
    q = uiapi.get("query")
    if not isinstance(q, dict):
        # No `query` block at all (e.g. objectInfos, currentUser) → non-row read.
        return None
    total = 0
    found_edges = False
    for _, v in q.items():
        if isinstance(v, dict) and isinstance(v.get("edges"), list):
            found_edges = True
            total += len(v["edges"])
    return total if found_edges else None


def is_grounding(path):
    name = os.path.basename(path)
    return name.startswith("ground-")


def eval_skill(org, name):
    reads_dir = os.path.join(EVAL_SKILLS_DIR, name, "reads")
    results = []
    if not os.path.isdir(reads_dir):
        return results
    for fn in sorted(os.listdir(reads_dir)):
        if not fn.endswith(".graphql"):
            continue
        path = os.path.join(reads_dir, fn)
        ok, detail, rows = run_graphql(org, path)
        expect_rows = not is_grounding(path)
        row_ok = (rows is None) or (not expect_rows) or (rows > 0)
        results.append({
            "read": fn,
            "reached_and_valid": ok,
            "rows": rows,
            "row_expectation_met": bool(ok and row_ok),
            "detail": detail,
        })
    return results


def discover_skills():
    if not os.path.isdir(EVAL_SKILLS_DIR):
        return []
    return sorted(
        d for d in os.listdir(EVAL_SKILLS_DIR)
        if os.path.isdir(os.path.join(EVAL_SKILLS_DIR, d, "reads"))
    )


def main(argv):
    org = None
    if "--org" in argv:
        i = argv.index("--org")
        org = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    as_json = "--json" in argv
    targets = [a for a in argv if not a.startswith("--")]

    if not org:
        print("error: --org <alias> is required (e.g. --org genwatt-demo)")
        return 2

    skills = targets if targets else discover_skills()
    report = {}
    overall_fail = False
    for name in skills:
        res = eval_skill(org, name)
        report[name] = res
        if any(not r["reached_and_valid"] or not r["row_expectation_met"] for r in res):
            overall_fail = True

    if as_json:
        print(json.dumps(report, indent=2))
        return 1 if overall_fail else 0

    print(f"Layer B read-connectivity eval  (org: {org}, READ-ONLY)")
    for name in skills:
        res = report[name]
        if not res:
            print(f"\n  {name}: (no reads/ fixtures)")
            continue
        print(f"\n  {name}:")
        for r in res:
            mark = "ok " if (r["reached_and_valid"] and r["row_expectation_met"]) else "FAIL"
            if r["detail"] == "aggregate":
                rows = "aggregate"
            else:
                rows = "grounding" if r["rows"] is None else f"{r['rows']} rows"
            extra = "" if r["reached_and_valid"] else f" — {r['detail']}"
            print(f"    [{mark}] {r['read']:<26} {rows}{extra}")

    print("\n" + ("=" * 52))
    print("RESULT:", "FAIL" if overall_fail else "PASS (reads valid on live org)")
    print("Note: trigger/routing, output rubric, and draft/never-send are host-run")
    print("      (agent runtime) checks — see eval.yaml; not exercised by this runner.")
    return 1 if overall_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
