#!/usr/bin/env python3
"""Deterministic local checks for the deal-advance-gap local changes.

The active skill carries four changes over the upstream source:

* the step 2a name-lookup correction filed upstream as #23 (open deals only, ``totalCount``, and
  one narrowing retry instead of offering a cut-off list);
* a stage-order correction filed upstream as #24: step 1 also returns the Stage picklist in
  the org's order, and the default target comes from it;
* a Quick/Kiro row-state rule; and
* a Quick/Kiro rule that labels unsourced exit criteria as suggested steps.
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
ACTIVE_SKILL = PLUGIN_ROOT / "skills" / "deal-advance-gap" / "SKILL.md"
SOURCE_SKILL = PLUGIN_ROOT.parent / "salesforce-for-sales" / "skills" / "deal-advance-gap" / "SKILL.md"
CANDIDATE_NEEDLE = 'Opportunity(where: { Name: { like: "%DEALNAME%" }'
GROUNDING_NEEDLE = 'objectInfos(apiNames: ["Opportunity"])'
MASTER_RECORD_TYPE = "012000000000000AAA"
Q = '\\\\\\"'  # a quote as written inside the skill's escaped queryInput strings

STAGES_MARKER = "`stages` lists the Stage picklist in the org's order"
STAGES_ANCHOR = "— never print a `__c` API name to the user.\n"
STATES_MARKER = "**Row states — Quick/Kiro adaptation:**"
STATE_CHECK = (
    "- [ ] Row states (Quick/Kiro adaptation): every row marked In motion or Scheduled names the open "
    "or future-dated task or event behind it in its `item` text. If it cannot, set that row to Not "
    "started; a completed touch awaiting a reply is never In motion.\n"
)
PAYLOAD_CHECK = (
    "- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block "
    'pasted as text. If the value starts with `"{"`, it is wrong.\n'
)
SUGGESTED_MARKER = "**Suggested steps — Quick/Kiro adaptation:**"
RULES_ANCHOR = "flag only elements that **block advancement**, not every unknown.\n"

TRUNCATION_RULE = (
    "- **`totalCount` above the rows returned** → the list is cut off and may not include the "
    "requested deal. Narrow `%DEALNAME%` (add the account or another distinctive word) and retry "
    "once; if it is still cut off, say how many open deals match and ask for the account. Never ask "
    "the user to choose from a cut-off list.\n"
)

# Exact source -> active replacements; together with the marked insertions below, nothing else
# in the skill may differ.
REPLACEMENTS = (
    (
        "Run a bounded, ordered candidate query (`%DEALNAME%` = 1–2 distinctive words):",
        "Run a bounded, ordered candidate query over open deals, since only an open deal can advance "
        "(`%DEALNAME%` = 1–2 distinctive words; when the request also names the account, use "
        "`%<account word>%<deal words>%`):",
    ),
    (
        f"Opportunity(where: {{ Name: {{ like: {Q}%DEALNAME%{Q} }} }}, orderBy: {{ CloseDate: {{ order: ASC }} }}, "
        "first: 10) { edges {",
        f"Opportunity(where: {{ Name: {{ like: {Q}%DEALNAME%{Q} }}, IsClosed: {{ eq: false }} }}, orderBy: "
        "{ CloseDate: { order: ASC } }, first: 10) { totalCount edges {",
    ),
    (
        "- **Exactly one** candidate → take its `Id`, go to 2b.\n",
        TRUNCATION_RULE + "- **Exactly one** candidate → take its `Id`, go to 2b.\n",
    ),
    (
        'childRelationships { childObjectApiName relationshipName } } } }\\"}" })',
        "childRelationships { childObjectApiName relationshipName } } "
        f"stages: objectInfos(objectInfoInputs: [{{ apiName: {Q}Opportunity{Q}, recordTypeIDs: [{Q}{MASTER_RECORD_TYPE}{Q}], "
        f"fieldNames: [{Q}StageName{Q}] }}]) {{ fields {{ ApiName ... on PicklistField {{ picklistValuesByRecordTypeIDs "
        '{ recordTypeID picklistValues { label value } } } } } } }\\"}" })',
    ),
    (
        'Target = next stage (default) or "to close" if asked.',
        "Target = the stage that follows the deal's current stage in step 1's `stages` order (default; "
        'when that is Closed Won, the target is to close), or "to close" if asked.',
    ),
    (PAYLOAD_CHECK, PAYLOAD_CHECK + STATE_CHECK),
)


def local_paragraph(text, marker):
    """Return the single-line local paragraph that starts with ``marker``."""
    start = text.index(marker)
    return text[start:text.index("\n", start)]


def section(text, heading, next_heading):
    start = text.index(heading)
    return text[start:text.index(next_heading, start)]


def documented_call(needle):
    calls = [call for call in e2e_calls.extract(["deal-advance-gap"]) if needle in call.get("query", "")]
    if len(calls) != 1:
        raise AssertionError(f"expected one deal-advance-gap call containing {needle!r}, found {len(calls)}")
    return calls[0]


def materialized_query(call):
    url, params, unresolved = e2e_calls.materialize(call)
    if unresolved:
        raise AssertionError(f"unresolved placeholders: {unresolved}")
    return url, json.loads(params["queryInput"])["query"]


class DealAdvanceGapMirrorDeltaTests(unittest.TestCase):
    def test_active_skill_is_the_source_plus_only_the_documented_changes(self):
        active = ACTIVE_SKILL.read_text()
        expected = SOURCE_SKILL.read_text()
        for old, new in REPLACEMENTS:
            self.assertEqual(1, expected.count(old), old[:70])
            expected = expected.replace(old, new)

        insertions = (
            (STAGES_ANCHOR, "\n" + local_paragraph(active, STAGES_MARKER) + "\n"),
            (
                RULES_ANCHOR,
                "\n" + local_paragraph(active, STATES_MARKER) + "\n\n" + local_paragraph(active, SUGGESTED_MARKER) + "\n",
            ),
        )
        for anchor, inserted in insertions:
            self.assertEqual(1, expected.count(anchor), anchor[:70])
            expected = expected.replace(anchor, anchor + inserted)

        self.assertEqual(expected, active)


class DealAdvanceGapLookupTests(unittest.TestCase):
    def test_source_lookup_has_no_open_filter_or_total(self):
        lookup = section(SOURCE_SKILL.read_text(), "## 2a. Resolve", "## 2b.")

        self.assertNotIn("IsClosed", lookup)
        self.assertNotIn("totalCount", lookup)

    def test_candidate_read_filters_open_deals_and_reports_the_total(self):
        url, query = materialized_query(documented_call(CANDIDATE_NEEDLE))

        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertIn('where: { Name: { like: "%a%" }, IsClosed: { eq: false } }', query)
        self.assertIn("orderBy: { CloseDate: { order: ASC } }, first: 10) { totalCount edges {", query)
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_instructions_narrow_a_cut_off_list_instead_of_offering_it(self):
        lookup = section(ACTIVE_SKILL.read_text(), "## 2a. Resolve", "## 2b.")

        self.assertIn("over open deals, since only an open deal can advance", lookup)
        self.assertIn("use `%<account word>%<deal words>%`", lookup)
        self.assertIn(TRUNCATION_RULE, lookup)
        self.assertLess(lookup.index(TRUNCATION_RULE), lookup.index("- **Exactly one** candidate"))
        self.assertLess(lookup.index("- **Exactly one** candidate"), lookup.index("- **Several**"))


class DealAdvanceGapStageOrderTests(unittest.TestCase):
    def test_source_grounding_returns_no_stage_order(self):
        source = SOURCE_SKILL.read_text()
        grounding = section(source, "## 1. Ground", "## 2a.")

        self.assertNotIn("PicklistField", grounding)
        self.assertIn('Target = next stage (default) or "to close" if asked.', source)

    def test_grounding_read_returns_the_stage_order_in_the_same_call(self):
        url, query = materialized_query(documented_call(GROUNDING_NEEDLE))

        self.assertEqual("/services/data/v65.0/graphql", url)
        self.assertIn(
            "objectInfos(apiNames: [\"Opportunity\"]) { fields { ApiName label relationshipName } "
            "childRelationships { childObjectApiName relationshipName } }",
            query,
        )
        self.assertIn(
            f'stages: objectInfos(objectInfoInputs: [{{ apiName: "Opportunity", recordTypeIDs: ["{MASTER_RECORD_TYPE}"], '
            'fieldNames: ["StageName"] }]) { fields { ApiName ... on PicklistField { picklistValuesByRecordTypeIDs '
            "{ recordTypeID picklistValues { label value } } } } }",
            query,
        )
        self.assertIsNone(validate.bracket_error(query, '"'))

    def test_target_stage_comes_from_the_returned_stage_order(self):
        active = ACTIVE_SKILL.read_text()
        grounding = section(active, "## 1. Ground", "## 2a.")

        self.assertIn(local_paragraph(active, STAGES_MARKER), grounding)
        self.assertIn("never infer the next stage from general sales knowledge", grounding)
        self.assertIn("Target = the stage that follows the deal's current stage in step 1's `stages` order", active)


class DealAdvanceGapAdaptationTests(unittest.TestCase):
    def setUp(self):
        self.active = ACTIVE_SKILL.read_text()
        self.mapping = section(self.active, "## 3. Map gaps", "## 4. Sequence")

    def test_rules_are_active_only_and_sit_in_the_gap_mapping_step(self):
        source = SOURCE_SKILL.read_text()
        for marker in (STATES_MARKER, SUGGESTED_MARKER):
            self.assertEqual(1, self.active.count(marker))
            self.assertNotIn(marker, source)
            self.assertIn(marker, self.mapping)

    def test_row_states_need_task_or_event_records(self):
        rule = local_paragraph(self.active, STATES_MARKER)
        for required in (
            "Take every Done, In motion, or Scheduled state from 2b's Tasks and Events",
            "Done needs a completed Task or a past-dated Event",
            "In motion or Scheduled needs an open Task or a future-dated Task or Event for that step",
            "A step that exists only as Next Step text, or a completed touch still awaiting a reply, is Not started",
        ):
            self.assertIn(required, rule)

    def test_widget_self_check_downgrades_unsupported_states(self):
        checks = section(self.active, "### Self-verification (before calling display_widget)", "The widget template is embedded below")

        self.assertIn(STATE_CHECK, checks)
        self.assertNotIn(STATE_CHECK, SOURCE_SKILL.read_text())
        self.assertLess(checks.index(PAYLOAD_CHECK), checks.index(STATE_CHECK))

    def test_unsourced_exit_criteria_are_labeled_as_suggested_steps(self):
        rule = local_paragraph(self.active, SUGGESTED_MARKER)
        for required in (
            "The documented reads do not return the org's exit criteria",
            "Unless the user names them, present the checklist as suggested steps instead of asking",
            "Base each step on this deal's returned data and cite it",
            "including `headerSubtitle` and `meterValueLabel`",
            "say in the callout that these are not the org's defined criteria",
        ):
            self.assertIn(required, rule)
        for token in ("{{headerSubtitle}}", "{{meterValueLabel}}", "{{calloutDescription}}"):
            self.assertIn(token, self.active)


if __name__ == "__main__":
    unittest.main()
