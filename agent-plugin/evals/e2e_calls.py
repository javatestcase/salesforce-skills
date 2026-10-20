#!/usr/bin/env python3
"""Run documented ``dispatch_readonly`` calls through the local read-only MCP adapter.

Every recognized call is extracted from ``skills/*/SKILL.md`` exactly as written. GraphQL and
SOQL calls use their documented query parameters; Configure's documented Opportunity Full/View
layout GET is also recognized as a narrowly defined scalar-parameter call.

Usage:
    python3 evals/e2e_calls.py --org <synthetic-org>
    python3 evals/e2e_calls.py --org <synthetic-org> configure
    python3 evals/e2e_calls.py --org <synthetic-org> --opportunity-id <synthetic-006-id> configure
    python3 evals/e2e_calls.py --list configure
"""

import json
import os
import re
import subprocess
import sys
import time

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(EVALS_DIR)
SKILLS_DIR = os.path.join(PLUGIN_ROOT, "skills")
SERVER = os.path.join(EVALS_DIR, "local-mcp", "salesforce-readonly-mcp")

CALL = re.compile(
    r'dispatch_readonly\(method: "GET", url: "([^"]+)",\s*'
    r'queryParams: \{ "(queryInput|q)": "((?:[^"\\]|\\.)*)" \}\)'
)
LAYOUT_CALL = re.compile(
    r'dispatch_readonly\(\s*method: "GET",\s*'
    r'url: "(/services/data/v63\.0/ui-api/records/<OPP_ID>)",\s*'
    r'queryParams: \{\s*"layoutTypes": "Full",\s*"modes": "View"\s*\}\s*\)',
    re.S,
)
PH = re.compile(r"<[A-Z][A-Za-z0-9_ …]*>|%[A-Z][A-Z0-9_]*%|\[[a-zA-Z]+\]")
OPPORTUNITY_ID_RE = re.compile(r"^006[0-9A-Za-z]{12}(?:[0-9A-Za-z]{3})?$")
CONFIGURE_LAYOUT_ID_SOQL = re.compile(
    r"^\s*SELECT\s+Id\s+FROM\s+Opportunity\s+ORDER\s+BY\s+LastModifiedDate\s+DESC\s+LIMIT\s+1\s*$",
    re.I,
)

ID = {
    "USER": "005000000000000AAA",
    "ACCOUNT": "001000000000000AAA",
    "OPP": "006000000000000AAA",
    "EVENT": "00U000000000000AAA",
}

FILL = {
    "'<ID1>','<ID2>',...": f"'{ID['ACCOUNT']}'",
    "<Event AccountId 001…>": ID["ACCOUNT"],
    "%SCOPE%": "scope: MINE",
    "<COMPANY>": "a",
    "<DOMAIN>": "a",
    "<HISTORY_CHILD>": "OpportunityHistories",
    "<USER_AMOUNT>": "0",
    "<USER_PRODUCT>": "a",
    "<OPPORTUNITY_ID>": ID["OPP"],
    "[recordId]": ID["ACCOUNT"],
    "<STALE_CUTOFF>": "2026-09-01",
    "<TODAY>": "2026-09-26",
    "<LEAD_FILTER>": 'Name: { like: "%a%" }',
    "<ACTIVITY_ACCOUNT_FILTER>": f'AccountId: {{ eq: "{ID["ACCOUNT"]}" }}',
    "<DOMAIN_FILTER>": 'Name: { like: "%a%" }',
    "<Q_START>": "2026-07-01",
    "<Q_END>": "2026-09-30",
    "%QSTART%": "2026-07-01",
    "%QEND%": "2026-09-30",
    "%START%": "2026-07-01",
    "%END%": "2026-09-30",
    "<OFFSET_START>": "1",
    "<OFFSET_END>": "7",
    "<UserId>": ID["USER"],
    "<USER_ID>": ID["USER"],
    "<CURRENT_USER_ID>": ID["USER"],
    "%OWNERID%": ID["USER"],
    "<UID>": ID["USER"],
    "<REP_ID>": ID["USER"],
    "<REP_PREFIX>": "a",
    "<NEXTSTEP>": "NextStep",
    "<ID>": ID["ACCOUNT"],
    "<OPP_ID>": ID["OPP"],
    "<ACCOUNT_ID>": ID["ACCOUNT"],
    "<EventId>": ID["EVENT"],
    "<ATTENDEE_EMAILS>": '"nobody@example.com"',
    "[objectName]": "Account",
    "[match]": "a",
}
SKILL_FILL = {
    "calendar-events": {
        "%START%": "2026-09-26T00:00:00.000Z",
        "%END%": "2026-09-27T00:00:00.000Z",
    },
}
LIST_FILL = {"<TEAM_USER_IDS>": ID["USER"]}
EMPTY = re.compile(r"<[A-Z_]*CUSTOM>|<REL_BLOCKS>")


def replace_common(value, skill=""):
    for key, replacement in SKILL_FILL.get(skill, {}).items():
        value = value.replace(key, replacement)
    for key, replacement in FILL.items():
        value = value.replace(key, replacement)
    return value


def fill(value, kind, skill=""):
    value = replace_common(value, skill)
    quote = '"' if kind == "queryInput" else "'"
    for key, replacement in LIST_FILL.items():
        value = value.replace(key, f"{quote}{replacement}{quote}")
    value = EMPTY.sub("", value)
    return re.sub(r"%[A-Z][A-Z0-9_]*%", "%a%", value)


def placeholders(values):
    return sorted({placeholder for value in values for placeholder in PH.findall(value)})


def extract(only=None):
    calls = []
    for skill in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, skill, "SKILL.md")
        if (only and skill not in only) or not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as source:
            text = source.read()
        for match in CALL.finditer(text):
            url, kind, raw = match.groups()
            value = json.loads('"' + raw + '"')
            query = json.loads(value)["query"] if kind == "queryInput" else value
            calls.append({
                "skill": skill,
                "line": text.count("\n", 0, match.start()) + 1,
                "url": url,
                "kind": kind,
                "query": query,
                "offset": match.start(),
            })
        for match in LAYOUT_CALL.finditer(text):
            calls.append({
                "skill": skill,
                "line": text.count("\n", 0, match.start()) + 1,
                "url": match.group(1),
                "kind": "layout",
                "params": {"layoutTypes": "Full", "modes": "View"},
                "offset": match.start(),
            })
    calls.sort(key=lambda call: (call["skill"], call["offset"]))
    for call in calls:
        call.pop("offset", None)
    return calls


def is_configure_layout_lookup(call):
    return (
        call["skill"] == "configure"
        and call["kind"] == "q"
        and CONFIGURE_LAYOUT_ID_SOQL.fullmatch(call["query"]) is not None
    )


def opportunity_id_from_response(text):
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records:
        return None
    candidate = records[0].get("Id") if isinstance(records[0], dict) else None
    return candidate if isinstance(candidate, str) and OPPORTUNITY_ID_RE.fullmatch(candidate) else None


def materialize(call, opportunity_id=None):
    """Return a dispatch-ready URL, query params, and unresolved placeholders."""
    if call["kind"] == "layout":
        if not opportunity_id:
            return None, None, ["<OPP_ID>"]
        url = call["url"].replace("<OPP_ID>", opportunity_id)
        params = dict(call["params"])
        return url, params, placeholders([url, *params.values()])

    query = fill(call["query"], call["kind"], call["skill"])
    url = fill(call["url"], "scalar", call["skill"])
    params = {"queryInput": json.dumps({"query": query})} if call["kind"] == "queryInput" else {"q": query}
    return url, params, placeholders([url, query])


class Server:
    def __init__(self, org):
        env = dict(os.environ, SF_TARGET_ORG=org)
        self.p = subprocess.Popen(
            [SERVER], cwd=PLUGIN_ROOT, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        self.nid = 0

    def rpc(self, method, params=None):
        self.nid += 1
        message = {"jsonrpc": "2.0", "id": self.nid, "method": method, "params": params or {}}
        self.p.stdin.write(json.dumps(message) + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def dispatch(self, args):
        result = self.rpc("tools/call", {"name": "dispatch_readonly", "arguments": args})["result"]
        return result["isError"], result["content"][0]["text"]

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)


GUARDS = [
    ("POST", {"method": "POST", "url": "/services/data/v65.0/graphql", "queryParams": {"queryInput": '{"query":"query { uiapi { currentUser { Id } } }"}'}}),
    ("sobjects endpoint", {"method": "GET", "url": "/services/data/v65.0/sobjects/Account", "queryParams": {}}),
    ("GraphQL mutation", {"method": "GET", "url": "/services/data/v65.0/graphql", "queryParams": {"queryInput": '{"query":"mutation { uiapi { AccountCreate(input: {}) { Record { Id } } } }"}'}}),
    ("non-SELECT SOQL", {"method": "GET", "url": "/services/data/v63.0/query", "queryParams": {"q": "DELETE FROM Account"}}),
    ("UI API wrong record type", {"method": "GET", "url": "/services/data/v63.0/ui-api/records/001000000000000AAA", "queryParams": {"layoutTypes": "Full", "modes": "View"}}),
    ("UI API extra parameter", {"method": "GET", "url": "/services/data/v63.0/ui-api/records/006000000000000AAA", "queryParams": {"layoutTypes": "Full", "modes": "View", "extra": "no"}}),
]


def parse_args(argv):
    org = None
    opportunity_id = None
    if "--org" in argv:
        index = argv.index("--org")
        if index + 1 >= len(argv):
            raise ValueError("--org needs an sf org alias")
        org = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]
    if "--opportunity-id" in argv:
        index = argv.index("--opportunity-id")
        if index + 1 >= len(argv):
            raise ValueError("--opportunity-id needs an Opportunity Id")
        opportunity_id = argv[index + 1]
        if not OPPORTUNITY_ID_RE.fullmatch(opportunity_id):
            raise ValueError("--opportunity-id must be a 15- or 18-character Opportunity Id")
        argv = argv[:index] + argv[index + 2:]
    return org, opportunity_id, argv


def main(argv):
    try:
        org, layout_opportunity_id, argv = parse_args(argv)
    except ValueError as error:
        print(f"error: {error}")
        return 2
    only = [argument for argument in argv if not argument.startswith("--")] or None
    calls = extract(only)

    if "--list" in argv:
        for call in calls:
            source = [call["url"], call.get("query", ""), *call.get("params", {}).values()]
            found = " ".join(placeholders(source)) or "-"
            print(f"{call['skill']}:{call['line']:<5} {call['kind']:<10} {call['url']:<48} {found}")
        print(f"\n{len(calls)} calls")
        return 0
    if not org:
        print("error: --org <alias> is required (use a sandbox org with synthetic data)")
        return 2
    if not os.access(SERVER, os.X_OK):
        print(f"error: local server not executable: {SERVER}")
        return 2

    server = Server(org)
    server.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "e2e_calls", "version": "1"}})
    print(f"E2E Salesforce calls  (org: {org}, READ-ONLY via local dispatch_readonly)")

    print("\nguards (must be rejected without calling Salesforce):")
    guard_fail = 0
    for label, args in GUARDS:
        started = time.time()
        is_error, text = server.dispatch(args)
        held = is_error and "rejected" in text and time.time() - started < 1
        guard_fail += not held
        print(f"  [{'ok ' if held else 'FAIL'}] {label}")

    print(f"\n{len(calls)} skill calls:")
    ok = fail = gap = skipped = 0
    per = {}
    for call in calls:
        url, params, left = materialize(call, layout_opportunity_id)
        if call["kind"] == "layout" and layout_opportunity_id is None:
            skipped += 1
            print(f"  [SKIP] {call['skill']}:{call['line']} layout read (no accessible Opportunity Id)")
            continue
        args = {"method": "GET", "url": url, "queryParams": params}
        is_error, text = server.dispatch(args)
        for wait in (2, 5):
            if not (is_error and text.startswith("error: no JSON from sf")):
                break
            time.sleep(wait)
            is_error, text = server.dispatch(args)
        count = per.setdefault(call["skill"], [0, 0])
        count[0] += 1
        if not is_error and not left:
            ok += 1
            if is_configure_layout_lookup(call):
                layout_opportunity_id = opportunity_id_from_response(text) or layout_opportunity_id
            continue
        count[1] += 1
        message = re.sub(r"\s+", " ", text)[:200]
        if left:
            gap += 1
            print(f"  [GAP ] {call['skill']}:{call['line']} unfilled {left} :: {message}")
        else:
            fail += 1
            print(f"  [FAIL] {call['skill']}:{call['line']} {url} :: {message}")
    server.close()

    print("\nper skill (calls/failures): " + "  ".join(f"{name}={values[0]}/{values[1]}" for name, values in sorted(per.items())))
    print("\n" + "=" * 52)
    print(f"RESULT: {ok} ok, {fail} failed, {gap} unfilled, {skipped} skipped, of {len(calls)}; guards failed: {guard_fail}")
    return 0 if not (fail or gap or guard_fail) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
