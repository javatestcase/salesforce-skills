#!/usr/bin/env python3
"""Deterministic local checks for the daily-briefing local changes.

The active skill carries three changes over the upstream source:

* a Quick/Kiro row-name rule for the closing-soon and past-due datagrids;
* a Quick/Kiro inbox-check rule, so the email checks are run and reported rather than dropped;
  and
* a meeting-account correction filed upstream as #22: the calendar read selects Event
  ``AccountId`` and the meeting-account read uses it, so Opportunity-linked meetings resolve to
  their Account through documented reads.
"""

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

E2E_SPEC = importlib.util.spec_from_file_location("e2e_calls", HERE / "e2e_calls.py")
e2e_calls = importlib.util.module_from_spec(E2E_SPEC)
E2E_SPEC.loader.exec_module(e2e_calls)

VALIDATE_SPEC = importlib.util.spec_from_file_location("validate", HERE / "validate.py")
validate = importlib.util.module_from_spec(VALIDATE_SPEC)
VALIDATE_SPEC.loader.exec_module(validate)

PLUGIN_ROOT = HERE.parent
ACTIVE_SKILL = PLUGIN_ROOT / "skills" / "daily-briefing" / "SKILL.md"
SOURCE_SKILL = PLUGIN_ROOT.parent / "salesforce-for-sales" / "skills" / "daily-briefing" / "SKILL.md"

ROW_NAME_MARKER = "**Row names — Quick/Kiro adaptation:**"
ROW_NAME_ANCHOR = "do not send empty arrays or leave stray {{tokens}}.\n"
INBOX_MARKER = "**Inbox check — Quick/Kiro adaptation:**"
INBOX_ANCHOR = "Sender, subject, domain only — don't read bodies (that's `inbox-sweep`).\n"
ACCOUNT_PLACEHOLDER = "<Event AccountId 001…>"

# Exact source -> active replacements for the meeting-account correction.
ACCOUNT_LOOKUP_EDITS = (
    (
        "Pull the raw `WhatId` / `WhoId` scalars instead. `WhatId` is your best account link — a "
        "`001…` Id is an Account, `006…` an Opportunity — resolve it directly in step 3 (no "
        "domain-guessing for those).",
        "Pull the raw `WhatId` / `WhoId` scalars instead, plus the standard `AccountId`. "
        "`AccountId` is your best account link: Salesforce derives it from the related record, so "
        "an Opportunity-linked (`006…`) meeting carries that Opportunity's Account. Use it directly "
        "in step 3 (no domain-guessing for those); `WhatId` still identifies the specific record "
        "(`001…` Account, `006…` Opportunity).",
    ),
    (
        "WhatId { value } WhoId { value } Description { value }",
        "WhatId { value } WhoId { value } AccountId { value } Description { value }",
    ),
    (
        "Extract each event's external-attendee email domains and its `WhatId`; those are the "
        "input to step 3.",
        "Extract each event's `AccountId`, `WhatId`, and external-attendee email domains; those "
        "are the input to step 3.",
    ),
    (
        "(a) any `WhatId` from 2a that is an Account (`001…`) → `Id: { eq }`, or an Opportunity "
        "(`006…`) → its `AccountId`; (b) the external-attendee domains → `Website` `like`. Prefer "
        "the direct `WhatId` link when present — it's exact; fall back to domain match only for "
        "meetings with no usable `WhatId`.",
        "(a) every non-null `AccountId` from 2a → `Id: { in }`; (b) the external-attendee domains "
        "→ `Website` `like`. Prefer the `AccountId` link when present — it's exact; fall back to "
        "domain match only for meetings with no `AccountId`.",
    ),
    ("<WhatId account 001…>", ACCOUNT_PLACEHOLDER),
)


def local_rule(text, marker):
    """Return the single-line local rule that starts with ``marker``."""
    start = text.index(marker)
    return text[start:text.index("\n", start)]


def row_name_rule(text):
    return local_rule(text, ROW_NAME_MARKER)


def inbox_rule(text):
    return local_rule(text, INBOX_MARKER)


def documented_call(needle):
    """Return the one active daily-briefing call whose query contains ``needle``."""
    calls = [call for call in e2e_calls.extract(["daily-briefing"]) if needle in call.get("query", "")]
    if len(calls) != 1:
        raise AssertionError(f"expected one daily-briefing call containing {needle!r}, found {len(calls)}")
    return calls[0]


def materialized_query(call):
    url, params, unresolved = e2e_calls.materialize(call)
    if unresolved:
        raise AssertionError(f"unresolved placeholders: {unresolved}")
    return url, json.loads(params["queryInput"])["query"]


class DailyBriefingMirrorDeltaTests(unittest.TestCase):
    def test_active_skill_is_the_source_plus_only_the_documented_changes(self):
        source = SOURCE_SKILL.read_text()
        active = ACTIVE_SKILL.read_text()

        expected = source
        for old, new in ACCOUNT_LOOKUP_EDITS:
            self.assertEqual(1, expected.count(old), old[:70])
            expected = expected.replace(old, new)
        for anchor, rule in ((ROW_NAME_ANCHOR, row_name_rule(active)), (INBOX_ANCHOR, inbox_rule(active))):
            self.assertEqual(1, expected.count(anchor))
            expected = expected.replace(anchor, anchor + "\n" + rule + "\n")

        self.assertEqual(expected, active)


class DailyBriefingRowNameTests(unittest.TestCase):
    def setUp(self):
        self.active = ACTIVE_SKILL.read_text()

    def test_rule_is_active_only_and_follows_the_row_contract(self):
        self.assertEqual(1, self.active.count(ROW_NAME_MARKER))
        self.assertNotIn(ROW_NAME_MARKER, SOURCE_SKILL.read_text())

        # The rule sits between the token contract and the renderer template it governs.
        tokens = self.active.index("Tokens: `dateEyebrow briefingTitle`")
        rule = self.active.index(ROW_NAME_MARKER)
        self.assertLess(tokens, rule)
        self.assertLess(rule, self.active.index('```json\n{\n  "renderer"', tokens))

    def test_rule_keeps_names_verbatim(self):
        rule = row_name_rule(self.active)
        for required in (
            "Copy each `closingRows` and `pastDueRows` `name` from the returned values",
            "If `Opportunity.Name` already begins with `Account.Name`, use `Opportunity.Name` unchanged",
            "otherwise use `<Account> — <Opp Name>`",
            "Never retype, shorten, or reword a name",
        ):
            self.assertIn(required, rule)


class DailyBriefingInboxCheckTests(unittest.TestCase):
    def setUp(self):
        self.active = ACTIVE_SKILL.read_text()

    def test_rule_is_active_only_and_sits_with_the_inbox_read(self):
        self.assertEqual(1, self.active.count(INBOX_MARKER))
        self.assertNotIn(INBOX_MARKER, SOURCE_SKILL.read_text())

        rule = self.active.index(INBOX_MARKER)
        self.assertLess(self.active.index("**2d. Inbox signal**"), rule)
        self.assertLess(rule, self.active.index("**2e. Running user**"))

    def test_rule_requires_the_check_and_an_explicit_result(self):
        rule = inbox_rule(self.active)
        for required in (
            "When an email tool is available, run this inbox read and step 3's \"you owe them\" search",
            "they are part of the briefing, not optional",
            "the follow-ups stat (`kpiFollowupsLine`/`kpiFollowupsSub`) and the owe/inbox block",
            "using `inboxClear` when nothing is found",
            "say the inbox was not checked",
            "Never drop them silently",
        ):
            self.assertIn(required, rule)

        # The rule must name tokens that the widget template actually renders.
        for token in ("{{kpiFollowupsLine}}", "{{kpiFollowupsSub}}", "{{inboxClear}}", "{{oweHeading}}"):
            self.assertIn(token, self.active)


class DailyBriefingMeetingAccountTests(unittest.TestCase):
    def test_source_has_no_documented_read_for_an_opportunity_link(self):
        source = SOURCE_SKILL.read_text()

        self.assertIn("an Opportunity (`006…`) → its `AccountId`", source)
        self.assertNotIn("AccountId { value }", source)

    def test_calendar_read_selects_event_account_id(self):
        url, query = materialized_query(documented_call("Event(scope: MINE"))

        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertIn("WhatId { value } WhoId { value } AccountId { value } Description { value }", query)
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_meeting_account_read_takes_event_account_ids(self):
        call = documented_call("Account(where: { or: [")
        self.assertIn(f'Id: {{ in: ["{ACCOUNT_PLACEHOLDER}"] }}', call["query"])

        url, query = materialized_query(call)
        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertIn(f'Id: {{ in: ["{e2e_calls.ID["ACCOUNT"]}"] }}', query)
        self.assertIn("Opportunities(where: { IsClosed: { eq: false } }, first: 5", query)
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_instructions_resolve_meetings_through_account_id(self):
        active = ACTIVE_SKILL.read_text()

        for required in (
            "plus the standard `AccountId`",
            "Extract each event's `AccountId`, `WhatId`, and external-attendee email domains",
            "(a) every non-null `AccountId` from 2a → `Id: { in }`",
            "fall back to domain match only for meetings with no `AccountId`",
        ):
            self.assertIn(required, active)
        self.assertNotIn("→ its `AccountId`", active)
        self.assertNotIn("<WhatId account 001…>", active)


if __name__ == "__main__":
    unittest.main()
