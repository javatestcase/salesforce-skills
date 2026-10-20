#!/usr/bin/env python3
"""Deterministic local checks for the deal-review local corrections.

The active skill carries two corrections over the upstream source:

* a multiple-match correction: the step 2 read takes the latest-closing match for 1–2 words with
  ``first: 1``, so a different deal can be reviewed silently. The active read selects
  ``totalCount``, and a documented candidate read resolves several matches to the requested deal
  or asks; and
* a stage-order correction: the widget's stage tile needs the deal's stage position and the stages
  left to close, so step 1 also returns the Stage picklist in the org's order (the same read added
  for deal-advance-gap).
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

TEMPLATES_SPEC = importlib.util.spec_from_file_location(
    "active_widget_templates", HERE / "mcp_apps" / "active_widget_templates.py"
)
active_widget_templates = importlib.util.module_from_spec(TEMPLATES_SPEC)
TEMPLATES_SPEC.loader.exec_module(active_widget_templates)

PLUGIN_ROOT = HERE.parent
ACTIVE_SKILL = PLUGIN_ROOT / "skills" / "deal-review" / "SKILL.md"
SOURCE_SKILL = PLUGIN_ROOT.parent / "salesforce-for-sales" / "skills" / "deal-review" / "SKILL.md"
Q = '\\\\\\"'  # a quote as written inside the skill's escaped queryInput strings
MASTER_RECORD_TYPE = "012000000000000AAA"

STAGE_MARKER = "**Stage order — local correction:**"
STAGE_ANCHOR = "— never print a `__c` API name to the user.\n"
MULTI_MARKER = "**Multiple matches — local correction:**"
EMPTY_ANCHOR = "Empty `edges` → use a broad resolver"
GROUNDING_NEEDLE = 'objectInfos(apiNames: ["Opportunity"])'
RICH_NEEDLE = "OpportunityHistories(first: 200"
CANDIDATE_NEEDLE = "first: 10) { totalCount edges"

REPLACEMENTS = (
    (
        f'objectInfos(apiNames: [{Q}Opportunity{Q}]) {{ fields {{ ApiName label }} }} }} }}\\"}}" }})',
        f"objectInfos(apiNames: [{Q}Opportunity{Q}]) {{ fields {{ ApiName label }} }} "
        f"stages: objectInfos(objectInfoInputs: [{{ apiName: {Q}Opportunity{Q}, recordTypeIDs: [{Q}{MASTER_RECORD_TYPE}{Q}], "
        f"fieldNames: [{Q}StageName{Q}] }}]) {{ fields {{ ApiName ... on PicklistField {{ picklistValuesByRecordTypeIDs "
        '{ recordTypeID picklistValues { label value } } } } } } }\\"}" })',
    ),
    (
        "orderBy: { CloseDate: { order: DESC } }, first: 1) { edges {",
        "orderBy: { CloseDate: { order: DESC } }, first: 1) { totalCount edges {",
    ),
)


def local_paragraph(text, marker):
    start = text.index(marker)
    return text[start:text.index("\n", start)]


def multi_match_block(text):
    """Return the inserted multiple-match rule, bullets, and candidate read."""
    return text[text.index(MULTI_MARKER):text.index(EMPTY_ANCHOR)]


def section(text, heading, next_heading):
    start = text.index(heading)
    return text[start:text.index(next_heading, start)]


def documented_call(needle):
    calls = [call for call in e2e_calls.extract(["deal-review"]) if needle in call.get("query", "")]
    if len(calls) != 1:
        raise AssertionError(f"expected one deal-review call containing {needle!r}, found {len(calls)}")
    return calls[0]


def materialized_query(call):
    url, params, unresolved = e2e_calls.materialize(call)
    if unresolved:
        raise AssertionError(f"unresolved placeholders: {unresolved}")
    return url, json.loads(params["queryInput"])["query"]


class DealReviewMirrorDeltaTests(unittest.TestCase):
    def test_active_skill_is_the_source_plus_only_the_two_corrections(self):
        active = ACTIVE_SKILL.read_text()
        expected = SOURCE_SKILL.read_text()
        for old, new in REPLACEMENTS:
            self.assertEqual(1, expected.count(old), old[:70])
            expected = expected.replace(old, new)
        for anchor in (STAGE_ANCHOR, EMPTY_ANCHOR):
            self.assertEqual(1, expected.count(anchor), anchor)
        expected = expected.replace(STAGE_ANCHOR, STAGE_ANCHOR + "\n" + local_paragraph(active, STAGE_MARKER) + "\n")
        expected = expected.replace(EMPTY_ANCHOR, multi_match_block(active) + EMPTY_ANCHOR)

        self.assertEqual(expected, active)

    def test_widget_blocks_match_upstream(self):
        self.assertIsNotNone(active_widget_templates.assert_active_widget_parity("deal-review"))


class DealReviewMultipleMatchTests(unittest.TestCase):
    def setUp(self):
        self.active = ACTIVE_SKILL.read_text()

    def test_source_read_cannot_see_other_matches(self):
        source = SOURCE_SKILL.read_text()
        read = section(source, "## 2. Read", "## 2b.")

        self.assertIn("first: 1) { edges {", read)
        self.assertNotIn("totalCount", read)

    def test_step_2_read_reports_the_match_count(self):
        url, query = materialized_query(documented_call(RICH_NEEDLE))

        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertIn('Opportunity(where: { Name: { like: "%a%" } }, orderBy: { CloseDate: { order: DESC } }, first: 1) { totalCount edges {', query)
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_candidate_read_is_documented_with_the_same_filter(self):
        url, query = materialized_query(documented_call(CANDIDATE_NEEDLE))

        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertIn('Opportunity(where: { Name: { like: "%a%" } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { totalCount edges {', query)
        for field in ("Id", "Name { value }", "StageName { value displayValue }", "CloseDate { value }", "IsClosed { value }", "Account { Name { value } }"):
            self.assertIn(field, query)
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_rule_resolves_or_asks_before_using_the_result(self):
        block = multi_match_block(self.active)
        read = section(self.active, "## 2. Read", "## 2b.")

        self.assertIn(block, read)
        self.assertNotIn(MULTI_MARKER, SOURCE_SKILL.read_text())
        self.assertLess(read.index(RICH_NEEDLE.split("(")[0]), read.index(MULTI_MARKER))
        for required in (
            "When `totalCount` is above 1, run the candidate read below before using the result.",
            "If `totalCount` is above 10, its list would be cut off, so first narrow `%DEALNAME%` with the account or other words from the request",
            "never with a name from a returned deal",
            "- if the list is empty or still cut off (`totalCount` above the rows returned), or narrowing was needed and the request had nothing to narrow with, "
            "say how many deals matched and ask for the full deal name or the account instead of listing a partial set;",
            "- if exactly one candidate's `Name` equals the deal name the user gave, take it;",
            "- otherwise, if exactly one candidate is open, take it;",
            "- otherwise list the candidates (Account · Name · Stage · close) and ask which.",
            "Keep the step 2 result when the chosen deal is the one it returned; otherwise rerun the full template",
        ):
            self.assertIn(required, block)
        # Narrowing comes before the list is used, and the branches run in priority order.
        order = [
            block.index(text)
            for text in ("first narrow", "- if the list is empty or still cut off", "- if exactly one candidate's", "- otherwise, if exactly one", "- otherwise list")
        ]
        self.assertEqual(sorted(order), order)

    def test_narrowing_threshold_matches_the_candidate_page_size(self):
        block = multi_match_block(self.active)
        _, query = materialized_query(documented_call(CANDIDATE_NEEDLE))

        self.assertIn("If `totalCount` is above 10,", block)
        self.assertIn("first: 10) { totalCount edges", query)


class DealReviewStageOrderTests(unittest.TestCase):
    def test_source_grounding_returns_no_stage_order(self):
        grounding = section(SOURCE_SKILL.read_text(), "## 1. Ground", "## 2. Read")
        self.assertNotIn("PicklistField", grounding)

    def test_grounding_read_returns_the_stage_order_in_the_same_call(self):
        url, query = materialized_query(documented_call(GROUNDING_NEEDLE))

        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertIn('objectInfos(apiNames: ["Opportunity"]) { fields { ApiName label } }', query)
        self.assertIn(
            f'stages: objectInfos(objectInfoInputs: [{{ apiName: "Opportunity", recordTypeIDs: ["{MASTER_RECORD_TYPE}"], '
            'fieldNames: ["StageName"] }]) { fields { ApiName ... on PicklistField { picklistValuesByRecordTypeIDs '
            "{ recordTypeID picklistValues { label value } } } } }",
            query,
        )
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_stage_tile_values_come_from_the_returned_order(self):
        active = ACTIVE_SKILL.read_text()
        rule = local_paragraph(active, STAGE_MARKER)

        self.assertIn(rule, section(active, "## 1. Ground", "## 2. Read"))
        for required in (
            "Take `kpiStageNum` from the deal's position in it (two digits, for example `04`)",
            "`kpiStageSub` from the stages after it up to and including Closed Won",
            "Never infer either from general sales knowledge",
        ):
            self.assertIn(required, rule)
        for token in ("{{kpiStageNum}}", "{{kpiStageSub}}"):
            self.assertIn(token, active)


if __name__ == "__main__":
    unittest.main()
