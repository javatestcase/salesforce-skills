#!/usr/bin/env python3
"""
Layer A static validator for Agent Plugin skills.

Runs offline, deterministic checks over every skills/<name>/SKILL.md in the plugin
(no LLM, no Salesforce org, no dependencies). Prints a per-skill scorecard and exits
non-zero if any BLOCKER check fails, so it can gate CI.

Standard it implements (see evals/README.md):
- Discovery/trigger hygiene: frontmatter name+description valid, name == dir.
- Portability: SKILL.md length budget; no display_widget leakage; no discover/describe.
- Consent posture: per-skill read-only vs. draft-only assertions from evals/skills/<name>/eval.yaml.
- Packaging: no eval-only files (eval.yaml, reads/) inside a shipped skill folder.

Usage:
    python3 evals/validate.py                 # validate all skills
    python3 evals/validate.py daily-briefing  # validate one skill
    python3 evals/validate.py --json          # machine-readable output
"""

import os
import re
import sys
import json

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(PLUGIN_ROOT, "skills")
# Eval-only assets (eval.yaml, reads/) live outside the shipped skill folders.
EVAL_SKILLS_DIR = os.path.join(PLUGIN_ROOT, "evals", "skills")
# Files that belong to the eval harness and must never ship inside a skill folder.
EVAL_ONLY = ("eval.yaml", "reads")

# Spec-derived limits / patterns
NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")  # Agent Skills name rule
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
LINE_BUDGET = 500  # recommended SKILL.md ceiling
# Substrings that must NOT appear in a SKILL.md body. Salesforce reads use the Headless 360
# read tool `dispatch_readonly(`; its write tool `dispatch(`, the discovery tools, and the
# Claude widget are blocked.
FORBIDDEN = ["display_widget", "dispatch(", "discover(", "describe("]

# Severity levels
BLOCKER = "BLOCKER"   # fails the build
WARNING = "WARNING"   # reported, does not fail the build

# Salesforce calls inside a SKILL.md. GraphQL wraps the query in a JSON string under
# "queryInput"; SOQL passes the statement under "q".
CALL_START_RE = re.compile(r"\bdispatch_readonly\(")
GQL_ARG_RE = re.compile(r'"queryInput":\s*"((?:[^"\\]|\\.)*)"')
SOQL_ARG_RE = re.compile(r'"q":\s*"((?:[^"\\]|\\.)*)"')
CALL_WINDOW = 6000  # max chars from `dispatch_readonly(` to its argument
PAIRS = {")": "(", "]": "[", "}": "{"}


def bracket_error(s, quote):
    """Return None if (), [], {} are balanced and correctly nested outside string literals,
    else a short description of the first problem."""
    stack, in_str, i = [], False, 0
    while i < len(s):
        ch = s[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                in_str = False
        elif ch == quote:
            in_str = True
        elif ch in "([{":
            stack.append((ch, i))
        elif ch in PAIRS:
            if not stack or stack[-1][0] != PAIRS[ch]:
                return f"unexpected {ch!r} at char {i}"
            stack.pop()
        i += 1
    if in_str:
        return "unterminated string literal"
    if stack:
        opener, pos = stack[-1]
        return f"{len(stack)} unclosed bracket(s), last {opener!r} at char {pos}"
    return None


def salesforce_call_problems(text):
    """Check every dispatch_readonly call and bare `query {` line in a SKILL.md.

    Returns (n_checked, problems) where problems are "line N: ..." strings. A GraphQL call's
    queryInput must decode (JSON string -> JSON object with a "query" string) and the query's
    brackets must balance; a SOQL call's parentheses must balance."""
    problems, n = [], 0

    def line_of(pos):
        return text.count("\n", 0, pos) + 1

    for m in CALL_START_RE.finditer(text):
        window = text[m.end():m.end() + CALL_WINDOW]
        gql, soql = GQL_ARG_RE.search(window), SOQL_ARG_RE.search(window)
        first = min((a for a in (gql, soql) if a), key=lambda a: a.start(), default=None)
        n += 1
        where = f"line {line_of(m.start())}"
        if first is None:
            problems.append(f"{where}: dispatch_readonly call has no queryInput or q argument")
            continue
        if first is gql:
            try:
                body = json.loads(json.loads('"' + gql.group(1) + '"'))
                query = body["query"]
                if not isinstance(query, str):
                    raise TypeError
            except (json.JSONDecodeError, KeyError, TypeError):
                problems.append(f"{where}: queryInput is not a JSON string of {{\"query\": \"...\"}}")
                continue
            err = bracket_error(query, '"')
        else:
            try:
                err = bracket_error(json.loads('"' + soql.group(1) + '"'), "'")
            except json.JSONDecodeError:
                problems.append(f"{where}: SOQL q is not a valid JSON string")
                continue
        if err:
            problems.append(f"{where}: {err}")

    # Bare GraphQL lines (the older converted format), in case any remain.
    for m in re.finditer(r"^[ \t]*(query \{.*)$", text, re.M):
        n += 1
        err = bracket_error(m.group(1).replace('\\"', '"'), '"')
        if err:
            problems.append(f"line {line_of(m.start())}: {err}")
    return n, problems


def parse_frontmatter(text):
    """Return (frontmatter_dict, body_str). Minimal YAML: top-level `key: value` only."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:]
    fm = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            fm[key] = val
    return fm, body


def load_eval_spec(name):
    """Tolerant read of evals/skills/<name>/eval.yaml for the field Layer A needs: posture.
    Returns a dict; missing file -> {}."""
    path = os.path.join(EVAL_SKILLS_DIR, name, "eval.yaml")
    if not os.path.exists(path):
        return {}
    spec = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^\s*posture:\s*(\S+)', line)
            if m:
                spec["posture"] = m.group(1).strip().strip("\"'")
    return spec


def check_skill(name):
    """Run all Layer A checks for one skill. Returns (results, has_blocker)."""
    skill_dir = os.path.join(SKILLS_DIR, name)
    skill_md = os.path.join(skill_dir, "SKILL.md")
    results = []

    def add(ok, severity, label, detail=""):
        results.append({"ok": ok, "severity": severity, "label": label, "detail": detail})

    if not os.path.exists(skill_md):
        add(False, BLOCKER, "SKILL.md exists", f"missing {skill_md}")
        return results, True

    with open(skill_md, encoding="utf-8") as f:
        text = f.read()
    fm, body = parse_frontmatter(text)
    spec = load_eval_spec(name)

    # --- Packaging: eval-only files must not ship with the skill ---
    leaked = [item for item in EVAL_ONLY if os.path.exists(os.path.join(skill_dir, item))]
    add(not leaked, BLOCKER, "no eval-only files in skill folder",
        f"move {', '.join(leaked)} to evals/skills/{name}/" if leaked else "")

    # --- Discovery / frontmatter ---
    fm_name = fm.get("name", "")
    add(bool(fm_name), BLOCKER, "frontmatter has name", "" if fm_name else "no name:")
    if fm_name:
        add(bool(NAME_RE.match(fm_name)) and len(fm_name) <= MAX_NAME_LEN,
            BLOCKER, "name matches spec constraints", fm_name)
        add(fm_name == name, BLOCKER, "name == directory", f"{fm_name} vs {name}")

    desc = fm.get("description", "")
    add(bool(desc), BLOCKER, "frontmatter has description",
        "" if desc else "no description:")
    if desc:
        add(len(desc) <= MAX_DESC_LEN, WARNING, "description within 1024 chars",
            f"{len(desc)} chars")
        # A good trigger describes what + when; nudge if it looks too short.
        add(len(desc) >= 40, WARNING, "description is descriptive enough",
            f"{len(desc)} chars")

    # --- Portability / length ---
    n_lines = text.count("\n") + 1
    add(n_lines <= LINE_BUDGET, WARNING, f"SKILL.md <= {LINE_BUDGET} lines",
        f"{n_lines} lines")

    for token in FORBIDDEN:
        present = token in body
        add(not present, BLOCKER, f"no forbidden token: {token!r}",
            "found" if present else "")

    # --- Salesforce calls: decodable arguments, balanced brackets ---
    n_calls, call_problems = salesforce_call_problems(text)
    add(not call_problems, BLOCKER, "Salesforce queries parse with balanced brackets",
        "; ".join(call_problems[:5]) + (f" (+{len(call_problems) - 5} more)" if len(call_problems) > 5 else ""))

    # --- Consent posture (from eval.yaml) ---
    posture = spec.get("posture")
    if posture is None:
        add(False, WARNING, "eval.yaml declares posture",
            f"no evals/skills/{name}/eval.yaml or no posture: field")
    elif posture == "read-only":
        # Read-only skills must not describe creating/sending/mutating.
        write_hints = re.findall(
            r'\b(send the email|auto-send|create (?:a )?record|update (?:the )?record|POST /|PATCH /|DELETE /)\b',
            body, re.IGNORECASE)
        add(not write_hints, BLOCKER, "read-only skill has no write/send verbs",
            ", ".join(sorted(set(write_hints))) if write_hints else "")
    elif posture == "draft-only":
        # Draft-only skills must carry an explicit never-send contract.
        has_contract = re.search(r'never send|do not send|not sent|draft.only', body, re.IGNORECASE)
        add(bool(has_contract), BLOCKER, "draft-only skill states never-send contract",
            "" if has_contract else "no 'never send' language found")
    else:
        add(False, WARNING, "posture is a known value",
            f"unknown posture: {posture}")

    has_blocker = any((not r["ok"]) and r["severity"] == BLOCKER for r in results)
    return results, has_blocker


def discover_skills():
    if not os.path.isdir(SKILLS_DIR):
        return []
    return sorted(
        d for d in os.listdir(SKILLS_DIR)
        if os.path.isdir(os.path.join(SKILLS_DIR, d))
        and os.path.exists(os.path.join(SKILLS_DIR, d, "SKILL.md"))
    )


def main(argv):
    as_json = "--json" in argv
    targets = [a for a in argv if not a.startswith("--")]
    skills = targets if targets else discover_skills()
    if not skills:
        print("No skills found under", SKILLS_DIR)
        return 1

    overall_fail = False
    report = {}
    for name in skills:
        results, has_blocker = check_skill(name)
        report[name] = results
        overall_fail = overall_fail or has_blocker

    if as_json:
        print(json.dumps(report, indent=2))
        return 1 if overall_fail else 0

    for name in skills:
        results = report[name]
        blockers = sum(1 for r in results if not r["ok"] and r["severity"] == BLOCKER)
        warns = sum(1 for r in results if not r["ok"] and r["severity"] == WARNING)
        status = "FAIL" if blockers else ("WARN" if warns else "PASS")
        print(f"\n[{status}] {name}  ({blockers} blocker(s), {warns} warning(s))")
        for r in results:
            if r["ok"]:
                continue
            mark = "x" if r["severity"] == BLOCKER else "!"
            detail = f" — {r['detail']}" if r["detail"] else ""
            print(f"   {mark} [{r['severity']}] {r['label']}{detail}")

    print("\n" + ("=" * 48))
    print("RESULT:", "FAIL (blockers present)" if overall_fail else "PASS")
    return 1 if overall_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
