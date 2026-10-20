#!/usr/bin/env python3
"""Layer A static validator for Agent Plugin skills.

Runs offline, deterministic checks over every skills/<name>/SKILL.md in the plugin
(no LLM, no Salesforce org, no dependencies). Prints a per-skill scorecard and exits
non-zero if any BLOCKER check fails, so it can gate CI.

Standard it implements (see evals/README.md):
- Discovery/trigger hygiene: frontmatter name+description valid, name == dir.
- Tool safety: direct general dispatch calls are blocked; read-only call syntax is checked.
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
EVAL_SKILLS_DIR = os.path.join(PLUGIN_ROOT, "evals", "skills")
EVAL_ONLY = ("eval.yaml", "reads")

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
LINE_BUDGET = 500

BLOCKER = "BLOCKER"
WARNING = "WARNING"

CALL_START_RE = re.compile(r"\bdispatch_readonly\(")
GENERAL_DISPATCH_RE = re.compile(r"\bdispatch\s*\(")
GQL_ARG_RE = re.compile(r'"queryInput":\s*"((?:[^"\\]|\\.)*)"')
SOQL_ARG_RE = re.compile(r'"q":\s*"((?:[^"\\]|\\.)*)"')
PAIRS = {")": "(", "]": "[", "}": "{"}


def bracket_error(s, quote):
    """Return None when (), [], and {} are balanced outside string literals."""
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


def general_dispatch_call_problems(text):
    """Report executable general dispatch calls without matching dispatch_readonly."""
    return [
        f"line {text.count(chr(10), 0, match.start()) + 1}: direct dispatch call is not allowed"
        for match in GENERAL_DISPATCH_RE.finditer(text)
    ]


def dispatch_call_window(text, start):
    """Return one complete ``dispatch_readonly(...)`` argument window, or ``None``."""
    depth, quote, index = 1, None, start
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
        index += 1
    return None


def salesforce_call_problems(text):
    """Validate complete read-only call expressions and bare GraphQL lines."""
    problems, n = [], 0
    layout_shape = re.compile(
        r'\s*method:\s*"GET",\s*'
        r'url:\s*"/services/data/v63\.0/ui-api/records/<OPP_ID>",\s*'
        r'queryParams:\s*\{\s*"layoutTypes":\s*"Full",\s*"modes":\s*"View"\s*\}\s*\)\s*$',
        re.S,
    )

    def line_of(pos):
        return text.count("\n", 0, pos) + 1

    for match in CALL_START_RE.finditer(text):
        n += 1
        where = f"line {line_of(match.start())}"
        window = dispatch_call_window(text, match.end())
        if window is None:
            problems.append(f"{where}: dispatch_readonly call has an unclosed parenthesis")
            continue
        if layout_shape.fullmatch(window):
            continue
        gql, soql = GQL_ARG_RE.search(window), SOQL_ARG_RE.search(window)
        first = min((item for item in (gql, soql) if item), key=lambda item: item.start(), default=None)
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
            error = bracket_error(query, '"')
        else:
            try:
                error = bracket_error(json.loads('"' + soql.group(1) + '"'), "'")
            except json.JSONDecodeError:
                problems.append(f"{where}: SOQL q is not a valid JSON string")
                continue
        if error:
            problems.append(f"{where}: {error}")

    for match in re.finditer(r"^[ \t]*(query \{.*)$", text, re.M):
        n += 1
        error = bracket_error(match.group(1).replace('\\"', '"'), '"')
        if error:
            problems.append(f"line {line_of(match.start())}: {error}")
    return n, problems


def parse_frontmatter(text):
    """Return a minimal top-level YAML frontmatter map and the remaining body."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:]
    frontmatter = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            frontmatter[key] = value
    return frontmatter, body


def load_eval_spec(name):
    """Read the one eval-spec field needed by Layer A: posture."""
    path = os.path.join(EVAL_SKILLS_DIR, name, "eval.yaml")
    if not os.path.exists(path):
        return {}
    spec = {}
    with open(path, encoding="utf-8") as source:
        for line in source:
            match = re.match(r"^\s*posture:\s*(\S+)", line)
            if match:
                spec["posture"] = match.group(1).strip().strip("\"'")
    return spec


def check_skill(name):
    """Run all Layer A checks for one skill and return results plus blocker state."""
    skill_dir = os.path.join(SKILLS_DIR, name)
    skill_md = os.path.join(skill_dir, "SKILL.md")
    results = []

    def add(ok, severity, label, detail=""):
        results.append({"ok": ok, "severity": severity, "label": label, "detail": detail})

    if not os.path.exists(skill_md):
        add(False, BLOCKER, "SKILL.md exists", f"missing {skill_md}")
        return results, True

    with open(skill_md, encoding="utf-8") as source:
        text = source.read()
    frontmatter, body = parse_frontmatter(text)
    spec = load_eval_spec(name)

    leaked = [item for item in EVAL_ONLY if os.path.exists(os.path.join(skill_dir, item))]
    add(not leaked, BLOCKER, "no eval-only files in skill folder",
        f"move {', '.join(leaked)} to evals/skills/{name}/" if leaked else "")

    fm_name = frontmatter.get("name", "")
    add(bool(fm_name), BLOCKER, "frontmatter has name", "" if fm_name else "no name:")
    if fm_name:
        add(bool(NAME_RE.match(fm_name)) and len(fm_name) <= MAX_NAME_LEN,
            BLOCKER, "name matches spec constraints", fm_name)
        add(fm_name == name, BLOCKER, "name == directory", f"{fm_name} vs {name}")

    description = frontmatter.get("description", "")
    add(bool(description), BLOCKER, "frontmatter has description",
        "" if description else "no description:")
    if description:
        add(len(description) <= MAX_DESC_LEN, WARNING, "description within 1024 chars",
            f"{len(description)} chars")
        add(len(description) >= 40, WARNING, "description is descriptive enough",
            f"{len(description)} chars")

    n_lines = text.count("\n") + 1
    add(n_lines <= LINE_BUDGET, WARNING, f"SKILL.md <= {LINE_BUDGET} lines",
        f"{n_lines} lines")

    _, call_problems = salesforce_call_problems(text)
    add(not call_problems, BLOCKER, "Salesforce queries parse with balanced brackets",
        "; ".join(call_problems[:5]) + (f" (+{len(call_problems) - 5} more)" if len(call_problems) > 5 else ""))

    dispatch_problems = general_dispatch_call_problems(text)
    add(not dispatch_problems, BLOCKER, "no executable general dispatch calls",
        "; ".join(dispatch_problems[:5]) + (f" (+{len(dispatch_problems) - 5} more)" if len(dispatch_problems) > 5 else ""))

    posture = spec.get("posture")
    if posture is None:
        add(False, WARNING, "eval.yaml declares posture",
            f"no evals/skills/{name}/eval.yaml or no posture: field")
    elif posture == "read-only":
        write_hints = re.findall(
            r"\b(send the email|auto-send|create (?:a )?record|update (?:the )?record|POST /|PATCH /|DELETE /)\b",
            body, re.IGNORECASE)
        add(not write_hints, BLOCKER, "read-only skill has no write/send verbs",
            ", ".join(sorted(set(write_hints))) if write_hints else "")
    elif posture == "draft-only":
        has_contract = re.search(r"never send|do not send|not sent|draft.only", body, re.IGNORECASE)
        add(bool(has_contract), BLOCKER, "draft-only skill states never-send contract",
            "" if has_contract else "no 'never send' language found")
    else:
        add(False, WARNING, "posture is a known value", f"unknown posture: {posture}")

    has_blocker = any((not result["ok"]) and result["severity"] == BLOCKER for result in results)
    return results, has_blocker


def discover_skills():
    if not os.path.isdir(SKILLS_DIR):
        return []
    return sorted(
        directory for directory in os.listdir(SKILLS_DIR)
        if os.path.isdir(os.path.join(SKILLS_DIR, directory))
        and os.path.exists(os.path.join(SKILLS_DIR, directory, "SKILL.md"))
    )


def main(argv):
    as_json = "--json" in argv
    targets = [argument for argument in argv if not argument.startswith("--")]
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
        blockers = sum(1 for result in results if not result["ok"] and result["severity"] == BLOCKER)
        warnings = sum(1 for result in results if not result["ok"] and result["severity"] == WARNING)
        status = "FAIL" if blockers else ("WARN" if warnings else "PASS")
        print(f"\n[{status}] {name}  ({blockers} blocker(s), {warnings} warning(s))")
        for result in results:
            if result["ok"]:
                continue
            mark = "x" if result["severity"] == BLOCKER else "!"
            detail = f" — {result['detail']}" if result["detail"] else ""
            print(f"   {mark} [{result['severity']}] {result['label']}{detail}")

    print("\n" + ("=" * 48))
    print("RESULT:", "FAIL (blockers present)" if overall_fail else "PASS")
    return 1 if overall_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
