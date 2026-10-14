#!/usr/bin/env python3
"""
End-to-end Salesforce call check: send every `dispatch_readonly` call in skills/*/SKILL.md,
exactly as written, through the local MCP server (evals/local-mcp/salesforce-readonly-mcp)
against a connected org. READ-ONLY: the server accepts only GET reads.

Unlike run_reads.py (which runs simplified fixtures), this runs the skills' own calls. Each
template placeholder is filled with a dummy value in the format the skill tells the model to
use (e.g. ISO datetimes for %START%, single-quoted Ids in SOQL), so a failure means the call
breaks when filled as instructed.

Usage:
    python3 evals/e2e_calls.py --org genwatt-demo                 # all skills
    python3 evals/e2e_calls.py --org genwatt-demo forecast-narrative
    python3 evals/e2e_calls.py --list                             # placeholders per call, no org needed

Exit: 0 all calls ok and guards hold; 1 any call failed, any placeholder left unfilled, or a
guard didn't hold; 2 usage error.
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

CALL = re.compile(r'dispatch_readonly\(method: "GET", url: "([^"]+)",\s*'
                  r'queryParams: \{ "(queryInput|q)": "((?:[^"\\]|\\.)*)" \}\)')
PH = re.compile(r"<[A-Z][A-Za-z0-9_ …]*>|%[A-Z][A-Z0-9_]*%|\[[a-zA-Z]+\]")

ID = {"USER": "005000000000000AAA", "ACCOUNT": "001000000000000AAA", "OPP": "006000000000000AAA",
      "EVENT": "00U000000000000AAA"}

# Placeholder -> dummy value, in the format each skill documents. Values only need to make the
# call valid; matching data is optional. Order matters (longer patterns first).
FILL = {
    "'<ID1>','<ID2>',...": f"'{ID['ACCOUNT']}'",
    "<WhatId account 001…>": ID["ACCOUNT"],
    "%SCOPE%": "scope: MINE",
    "<COMPANY>": "a", "<DOMAIN>": "a",
    "<HISTORY_CHILD>": "OpportunityHistories",
    "<USER_AMOUNT>": "0", "<USER_PRODUCT>": "a",
    "<OPPORTUNITY_ID>": ID["OPP"], "[recordId]": ID["ACCOUNT"],
    "<STALE_CUTOFF>": "2026-09-01", "<TODAY>": "2026-09-26",
    "<LEAD_FILTER>": 'Name: { like: "%a%" }',
    "<ACTIVITY_ACCOUNT_FILTER>": f'AccountId: {{ eq: "{ID["ACCOUNT"]}" }}',
    "<DOMAIN_FILTER>": 'Name: { like: "%a%" }',
    "<Q_START>": "2026-07-01", "<Q_END>": "2026-09-30",            # YYYY-MM-DD
    "%QSTART%": "2026-07-01", "%QEND%": "2026-09-30",              # YYYY-MM-DD (forecast-narrative)
    "%START%": "2026-07-01", "%END%": "2026-09-30",                # date literals (win-loss-review)
    "<OFFSET_START>": "1", "<OFFSET_END>": "7",
    "<UserId>": ID["USER"], "<USER_ID>": ID["USER"], "<CURRENT_USER_ID>": ID["USER"], "%OWNERID%": ID["USER"],
    "<UID>": ID["USER"], "<REP_ID>": ID["USER"], "<REP_PREFIX>": "a",   # deal-signals, rep-context
    "<NEXTSTEP>": "NextStep",                                          # deal-signals default next-step field
    "<ID>": ID["ACCOUNT"], "<OPP_ID>": ID["OPP"], "<ACCOUNT_ID>": ID["ACCOUNT"], "<EventId>": ID["EVENT"],
    "<ATTENDEE_EMAILS>": '"nobody@example.com"',
    "[objectName]": "Account", "[match]": "a",
}
# Same placeholder name, different format in one skill: applied before FILL.
SKILL_FILL = {
    "calendar-events": {"%START%": "2026-09-26T00:00:00.000Z", "%END%": "2026-09-27T00:00:00.000Z"},  # "ISO boundaries"
}
# List placeholders are quoted per language: GraphQL "..." vs SOQL '...'.
LIST_FILL = {"<TEAM_USER_IDS>": ID["USER"]}
EMPTY = re.compile(r"<[A-Z_]*CUSTOM>|<REL_BLOCKS>")  # optional custom-field slots


def extract(only=None):
    calls = []
    for skill in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, skill, "SKILL.md")
        if (only and skill not in only) or not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        for m in CALL.finditer(text):
            url, kind, raw = m.groups()
            value = json.loads('"' + raw + '"')
            query = json.loads(value)["query"] if kind == "queryInput" else value
            calls.append({"skill": skill, "line": text.count("\n", 0, m.start()) + 1,
                          "url": url, "kind": kind, "query": query})
    return calls


def fill(q, kind, skill=""):
    for k, v in SKILL_FILL.get(skill, {}).items():
        q = q.replace(k, v)
    for k, v in FILL.items():
        q = q.replace(k, v)
    quote = '"' if kind == "queryInput" else "'"
    for k, v in LIST_FILL.items():
        q = q.replace(k, f"{quote}{v}{quote}")
    q = EMPTY.sub("", q)
    return re.sub(r"%[A-Z][A-Z0-9_]*%", "%a%", q)  # remaining %X% are LIKE patterns


class Server:
    def __init__(self, org):
        env = dict(os.environ, SF_TARGET_ORG=org)
        self.p = subprocess.Popen([SERVER], cwd=PLUGIN_ROOT, env=env, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.nid = 0

    def rpc(self, method, params=None):
        self.nid += 1
        msg = {"jsonrpc": "2.0", "id": self.nid, "method": method, "params": params or {}}
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def dispatch(self, args):
        r = self.rpc("tools/call", {"name": "dispatch_readonly", "arguments": args})["result"]
        return r["isError"], r["content"][0]["text"]

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)


GUARDS = [
    ("POST", {"method": "POST", "url": "/services/data/v65.0/graphql",
              "queryParams": {"queryInput": '{"query":"query { uiapi { currentUser { Id } } }"}'}}),
    ("sobjects endpoint", {"method": "GET", "url": "/services/data/v65.0/sobjects/Account", "queryParams": {}}),
    ("GraphQL mutation", {"method": "GET", "url": "/services/data/v65.0/graphql",
                          "queryParams": {"queryInput": '{"query":"mutation { uiapi { AccountCreate(input: {}) { Record { Id } } } }"}'}}),
    ("non-SELECT SOQL", {"method": "GET", "url": "/services/data/v63.0/query", "queryParams": {"q": "DELETE FROM Account"}}),
]


def main(argv):
    org = None
    if "--org" in argv:
        i = argv.index("--org")
        if i + 1 >= len(argv):
            print("error: --org needs an sf org alias")
            return 2
        org = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    only = [a for a in argv if not a.startswith("--")] or None
    calls = extract(only)

    if "--list" in argv:
        for c in calls:
            phs = sorted(set(PH.findall(c["query"])))
            print(f"{c['skill']}:{c['line']:<5} {c['url']:<36} {' '.join(phs) or '-'}")
        print(f"\n{len(calls)} calls")
        return 0
    if not org:
        print("error: --org <alias> is required (use a sandbox org with synthetic data)")
        return 2
    if not os.access(SERVER, os.X_OK):
        print(f"error: local server not executable: {SERVER}")
        return 2

    srv = Server(org)
    srv.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "e2e_calls", "version": "1"}})
    print(f"E2E Salesforce calls  (org: {org}, READ-ONLY via local dispatch_readonly)")

    print("\nguards (must be rejected without calling Salesforce):")
    guard_fail = 0
    for label, args in GUARDS:
        t = time.time()
        err, text = srv.dispatch(args)
        held = err and "rejected" in text and time.time() - t < 1
        guard_fail += not held
        print(f"  [{'ok ' if held else 'FAIL'}] {label}")

    print(f"\n{len(calls)} skill calls:")
    ok = fail = gap = 0
    per = {}
    for c in calls:
        q = fill(c["query"], c["kind"], c["skill"])
        left = sorted(set(PH.findall(q)))
        qp = {"queryInput": json.dumps({"query": q})} if c["kind"] == "queryInput" else {"q": q}
        args = {"method": "GET", "url": c["url"], "queryParams": qp}
        err, text = srv.dispatch(args)
        for wait in (2, 5):  # sf CLI occasionally exits 1 with no output; retry with backoff
            if not (err and text.startswith("error: no JSON from sf")):
                break
            time.sleep(wait)
            err, text = srv.dispatch(args)
        n = per.setdefault(c["skill"], [0, 0])
        n[0] += 1
        if not err and not left:
            ok += 1
            continue
        n[1] += 1
        msg = re.sub(r"\s+", " ", text)[:200]
        if left:
            gap += 1
            print(f"  [GAP ] {c['skill']}:{c['line']} unfilled {left} :: {msg}")
        else:
            fail += 1
            print(f"  [FAIL] {c['skill']}:{c['line']} {c['url']} :: {msg}")
    srv.close()

    print("\nper skill (calls/failures): " + "  ".join(f"{k}={v[0]}/{v[1]}" for k, v in sorted(per.items())))
    print("\n" + "=" * 52)
    print(f"RESULT: {ok} ok, {fail} failed, {gap} unfilled, of {len(calls)}; guards failed: {guard_fail}")
    return 0 if not (fail or gap or guard_fail) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
