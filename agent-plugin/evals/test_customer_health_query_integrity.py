#!/usr/bin/env python3
"""Deterministic local checks for the customer-health Quick/Kiro adaptations."""

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
ACTIVE_SKILL = PLUGIN_ROOT / "skills" / "customer-health" / "SKILL.md"
SOURCE_SKILL = PLUGIN_ROOT.parent / "salesforce-for-sales" / "skills" / "customer-health" / "SKILL.md"
LOCAL_MARKER = "**Canonical query execution — Quick/Kiro adaptation:**"
CASE_TOTALS_MARKER = "**Case totals — local correction:**"
ACCOUNT_NAME = 'Name: { like: "%ACCOUNT%" }'
ACCOUNT_ID = 'Id: { eq: "001000000000000AAA" }'
WINDOW = "CreatedDate: { gte: { literal: LAST_90_DAYS } }"
COUNT = "{ edges { node { aggregate { Id { count { value } } } } } }"


def deep_account_call():
    calls = [
        call
        for call in e2e_calls.extract(["customer-health"])
        if "Account(where:" in call.get("query", "")
    ]
    if len(calls) != 1:
        raise AssertionError(f"expected one customer-health deep Account call, found {len(calls)}")
    return calls[0]


def brace_depth(query, needle):
    """Return the selection-set depth before the first ``needle``, ignoring string literals."""
    depth, quoted = 0, False
    for char in query[: query.index(needle)]:
        if char == '"':
            quoted = not quoted
        elif not quoted and char == "{":
            depth += 1
        elif not quoted and char == "}":
            depth -= 1
    return depth


class CustomerHealthQueryIntegrityTests(unittest.TestCase):
    def test_local_adaptation_requires_preflight_before_first_dispatch(self):
        active = ACTIVE_SKILL.read_text()
        source = SOURCE_SKILL.read_text()

        self.assertIn(LOCAL_MARKER, active)
        self.assertNotIn(LOCAL_MARKER, source)
        for required in (
            "complete canonical `queryInput`, not an outline",
            "Before the first dispatch",
            "Do not send a reconstructed request",
            "discard that attempted request and rebuild once",
            "with `<ACCT_CUSTOM>` omitted",
            "report the error and stop",
            "Keep `aggregate` a sibling of `query` under `uiapi`",
        ):
            self.assertIn(required, active)

    def test_standard_field_materialization_preserves_the_canonical_shape(self):
        call = deep_account_call()
        url, params, unresolved = e2e_calls.materialize(call)

        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertEqual([], unresolved)
        query = json.loads(params["queryInput"])["query"]
        self.assertIsNone(validate.bracket_error(query, '"'))
        self.assertNotIn("<ACCT_CUSTOM>", query)
        for required in (
            'Account(where: { Name: { like: "%a%" } }, first: 1)',
            "Owner { Name { value } }",
            "Opportunities(first: 20",
            "Cases(first: 10",
            "Tasks(first: 20",
            'aggregate { matchedAccounts: Account(where: { Name: { like: "%a%" } })',
        ):
            self.assertIn(required, query)

    def test_exact_id_recovery_form_is_balanced_without_custom_fields(self):
        query = deep_account_call()["query"]
        query = query.replace(ACCOUNT_NAME, ACCOUNT_ID).replace("<ACCT_CUSTOM>", "")

        self.assertNotIn("%ACCOUNT%", query)
        self.assertNotIn("<ACCT_CUSTOM>", query)
        self.assertIsNone(validate.bracket_error(query, '"'))
        self.assertIn(f"Account(where: {{ {ACCOUNT_ID} }}, first: 1)", query)


class CustomerHealthCaseTotalsTests(unittest.TestCase):
    def test_aggregate_block_is_a_sibling_of_query_under_uiapi(self):
        query = deep_account_call()["query"]

        self.assertTrue(query.startswith("query { uiapi { query { Account("))
        self.assertEqual(2, brace_depth(query, "query { Account("))
        self.assertEqual(2, brace_depth(query, "aggregate { matchedAccounts:"))
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_case_totals_share_the_account_predicate_and_detail_window(self):
        query = deep_account_call()["query"]

        for expected in (
            f"matchedAccounts: Account(where: {{ {ACCOUNT_NAME} }}) {COUNT}",
            f"caseTotal: Case(where: {{ Account: {{ {ACCOUNT_NAME} }}, {WINDOW} }}) {COUNT}",
            f"caseOpen: Case(where: {{ Account: {{ {ACCOUNT_NAME} }}, {WINDOW}, IsClosed: {{ eq: false }} }}) {COUNT}",
            f'caseEscalated: Case(where: {{ Account: {{ {ACCOUNT_NAME} }}, {WINDOW}, Status: {{ eq: "Escalated" }} }}) {COUNT}',
            f'caseHighPriority: Case(where: {{ Account: {{ {ACCOUNT_NAME} }}, {WINDOW}, Priority: {{ in: ["High", "Critical"] }} }}) {COUNT}',
            f"Cases(first: 10, where: {{ {WINDOW} }}",
        ):
            self.assertIn(expected, query)

    def test_exact_id_form_replaces_every_account_predicate(self):
        query = deep_account_call()["query"].replace(ACCOUNT_NAME, ACCOUNT_ID).replace("<ACCT_CUSTOM>", "")

        self.assertNotIn("%ACCOUNT%", query)
        self.assertEqual(6, query.count(ACCOUNT_ID))
        self.assertEqual(4, query.count(f"Account: {{ {ACCOUNT_ID} }}"))
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_active_skill_takes_support_counts_from_aggregates(self):
        active = ACTIVE_SKILL.read_text()
        source = SOURCE_SKILL.read_text()

        self.assertIn(CASE_TOTALS_MARKER, active)
        self.assertNotIn(CASE_TOTALS_MARKER, source)
        self.assertNotIn("caseTotal", source)
        for required in (
            "Take every Support count from the `aggregate` roots",
            "only as the latest ten, never as the total",
            "If `matchedAccounts` is greater than 1",
            "never count the capped rows instead",
            "swap every `Name: { like: \\\"%ACCOUNT%\\\" }` predicate",
            "| Support | step 2 `aggregate` case counts",
        ):
            self.assertIn(required, active)


class CustomerHealthWidgetPayloadTests(unittest.TestCase):
    def test_active_skill_shows_object_not_string_payload_at_the_widget_call(self):
        active = ACTIVE_SKILL.read_text()
        source = SOURCE_SKILL.read_text()
        account_context = (PLUGIN_ROOT / "skills" / "account-context" / "SKILL.md").read_text()
        wrong = '- ❌ WRONG: `widgetDefinition: "{\\"renderer\\":{...}}"` (stringified with escaped quotes)'
        right = '- ✅ RIGHT: `widgetDefinition: {"renderer":{...}}` (native object, no quotes around opening brace)'

        self.assertIn("**Widget payload — Quick/Kiro adaptation:**", active)
        self.assertIn("parse it into an object before the call", active)
        self.assertNotIn("**Widget payload — Quick/Kiro adaptation:**", source)
        for example in (wrong, right):
            self.assertIn(example, active)
            self.assertIn(example, account_context)

        warning = active.index("**Widget payload — Quick/Kiro adaptation:**")
        self.assertLess(active.index("### Self-verification (before calling display_widget)"), warning)
        self.assertLess(warning, active.index("The widget template is embedded below"))


if __name__ == "__main__":
    unittest.main()
