#!/usr/bin/env python3
"""Deterministic local checks for the deal-signals local changes.

The active skill carries four changes over the upstream source:

* an output-choice correction filed upstream as #25: the widget is a single-opportunity
  buying-signal view whose composite score and six-week trend no step computes, so a book or team
  sweep returns the text digest, and a single-deal widget drops the chart-and-meter column;
* a Quick/Kiro stale-commitment rule that reads the already-fetched ``LastModifiedDate``;
* a Quick/Kiro email-evidence rule, so the email search runs when available and a skipped search
  is stated rather than implied clear; and
* a Quick/Kiro complete-digest rule, so no flagged deal is dropped to shorten the digest.
"""

import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

TEMPLATES_SPEC = importlib.util.spec_from_file_location(
    "active_widget_templates", HERE / "mcp_apps" / "active_widget_templates.py"
)
active_widget_templates = importlib.util.module_from_spec(TEMPLATES_SPEC)
TEMPLATES_SPEC.loader.exec_module(active_widget_templates)

PLUGIN_ROOT = HERE.parent
ACTIVE_SKILL = PLUGIN_ROOT / "skills" / "deal-signals" / "SKILL.md"
SOURCE_SKILL = PLUGIN_ROOT.parent / "salesforce-for-sales" / "skills" / "deal-signals" / "SKILL.md"
SCHEMA_PATH = PLUGIN_ROOT.parent / "salesforce-for-sales" / "skills" / "using-display-widget" / "widget-definition.schema.json"
TOKEN_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")

OUTPUT_MARKER = "**Output choice — local correction:**"
OUTPUT_ANCHOR = "## 4. Widget (default output when `display_widget` is present: Cowork/desktop/web)\n"
STALE_MARKER = "**Stale commitment — Quick/Kiro adaptation:**"
STALE_ANCHOR = "- **Competitor mention** — named in recent email/transcript\n"
EMAIL_MARKER = "**Email evidence — Quick/Kiro adaptation:**"
EMAIL_ANCHOR = "Keyed on the flagged account names. No tools present → skip silently.\n"
DIGEST_MARKER = "**Complete digest — Quick/Kiro adaptation:**"
DIGEST_ANCHOR = "Scheduled run: lead with count of new items since last run; a quiet digest is success.\n"

CHART_AND_METER_TOKENS = {
    "chartCaption", "chartCategories", "chartSeries", "meterLabel", "meterValue", "meterMax",
    "meterTarget", "meterValueLabel", "meterTargetLabel", "meterStatus", "meterBands",
}

# Realistic single-deal values for every token outside the chart-and-meter column.
SINGLE_DEAL_VALUES = {
    "title": "Deal signals — Example Co — New Business Upgrade",
    "headerStatus": "AT RISK",
    "subtitle": "2 risk signals",
    "dealContext": "Value Proposition · $1,296,000 · close 2026-12-14 · next: Legal review of MSA · last activity 2026-08-19",
    "datagridCaption": "Signals detected, strongest first",
    "datagridRows": [
        {
            "status": {"value": "Watch", "badgeVariant": "warning"},
            "signal": "Gone quiet",
            "dir": {"value": "Watch", "badgeVariant": "warning"},
            "when": "2026-08-19",
            "note": "No activity in 60 days; closes in 57 days",
        },
        {
            "status": {"value": "Watch", "badgeVariant": "warning"},
            "signal": "Stale commitment",
            "dir": {"value": "Watch", "badgeVariant": "warning"},
            "when": "2026-09-09",
            "note": "Next step unchanged since the last edit on 2026-09-09",
        },
    ],
    "calloutTitle": "Two months quiet with a stale next step",
    "calloutDescription": "Re-engage the decision maker this week and refresh the next step.",
    "primaryButtonLabel": "Draft re-engagement",
    "primaryButtonContent": "Draft a re-engagement email for this deal's decision maker.",
    "oppUrl": "https://example.invalid/lightning/r/Opportunity/006000000000000AAA/view",
}


def local_paragraph(text, marker):
    """Return the single-line local paragraph that starts with ``marker``."""
    start = text.index(marker)
    return text[start:text.index("\n", start)]


def section(text, heading, next_heading):
    start = text.index(heading)
    return text[start:text.index(next_heading, start)]


def renderer():
    widget = active_widget_templates.dynamic_renderer(ACTIVE_SKILL)
    if widget is None:
        raise AssertionError("deal-signals: dynamic renderer missing")
    return widget


def hydrate(value, values):
    """Substitute tokens; a key with no value is omitted so that leaf drops (the contract's rule)."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if isinstance(item, str):
                exact = TOKEN_RE.fullmatch(item)
                if exact and exact.group(1) not in values:
                    continue
            out[key] = hydrate(item, values)
        return out
    if isinstance(value, list):
        return [hydrate(item, values) for item in value]
    if isinstance(value, str):
        exact = TOKEN_RE.fullmatch(value)
        if exact:
            return values[exact.group(1)]
        return TOKEN_RE.sub(lambda match: str(values[match.group(1)]), value)
    return value


def without_chart_and_meter_column(widget):
    widget = copy.deepcopy(widget)
    root = widget["renderer"]["componentOverrides"]["$"]
    root["children"] = [child for child in root["children"] if child.get("definition") != "tile/column"]
    return widget


def required_attributes():
    """Map each tile definition to the attribute names the widget schema requires."""
    schema = json.loads(SCHEMA_PATH.read_text())
    requirements = {}
    for clause in schema["$defs"]["block"].get("allOf", []):
        definition = clause.get("if", {}).get("properties", {}).get("definition", {}).get("const")
        ref = clause.get("then", {}).get("properties", {}).get("attributes", {}).get("$ref")
        if definition and ref:
            requirements[definition] = schema["$defs"][ref.rsplit("/", 1)[-1]].get("required", [])
    return requirements


def schema_gaps(widget):
    """Return ``(definition, missing required attributes)`` for every incomplete tile."""
    requirements, gaps = required_attributes(), []

    def visit(node):
        if isinstance(node, dict):
            definition = node.get("definition")
            if definition in requirements:
                missing = [key for key in requirements[definition] if key not in (node.get("attributes") or {})]
                if missing:
                    gaps.append((definition, missing))
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(widget)
    return gaps


def definitions(widget):
    found = []

    def visit(node):
        if isinstance(node, dict):
            if isinstance(node.get("definition"), str):
                found.append(node["definition"])
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(widget)
    return found


class DealSignalsMirrorDeltaTests(unittest.TestCase):
    def test_active_skill_is_the_source_plus_only_the_three_rules(self):
        active = ACTIVE_SKILL.read_text()
        expected = SOURCE_SKILL.read_text()
        for anchor, marker in (
            (EMAIL_ANCHOR, EMAIL_MARKER),
            (STALE_ANCHOR, STALE_MARKER),
            (OUTPUT_ANCHOR, OUTPUT_MARKER),
            (DIGEST_ANCHOR, DIGEST_MARKER),
        ):
            self.assertEqual(1, expected.count(anchor), anchor[:60])
            expected = expected.replace(anchor, anchor + "\n" + local_paragraph(active, marker) + "\n")

        self.assertEqual(expected, active)

    def test_widget_blocks_match_upstream(self):
        self.assertIsNotNone(active_widget_templates.assert_active_widget_parity("deal-signals"))


class DealSignalsOutputChoiceTests(unittest.TestCase):
    def setUp(self):
        self.active = ACTIVE_SKILL.read_text()

    def test_rule_comes_before_the_widget_call(self):
        widget_section = section(self.active, "## 4. Widget", "### Self-verification")
        rule = widget_section.index(OUTPUT_MARKER)
        self.assertLess(rule, widget_section.index("When the data is assembled, call `display_widget`"))
        self.assertNotIn(OUTPUT_MARKER, SOURCE_SKILL.read_text())

    def test_rule_wording(self):
        rule = local_paragraph(self.active, OUTPUT_MARKER)
        for required in (
            "no step computes its composite score or six-week score trend",
            "For a book or team sweep, do not call `display_widget`; the step 5 digest is the final output",
            "overriding the widget-first rule",
            "When the request names one deal that is in the step 2 results",
            "remove the `tile/column` that holds the chart and meter",
            "Give signal counts only in `subtitle`",
            "use Watch for each risk row's `status` and `dir`",
            'skip the "two graphs present" check',
            "Never invent a score or a trend",
        ):
            self.assertIn(required, rule)

    def test_chart_and_meter_tokens_live_only_in_the_one_column(self):
        root = renderer()["renderer"]["componentOverrides"]["$"]
        columns = [child for child in root["children"] if child.get("definition") == "tile/column"]

        self.assertEqual(1, len(columns))
        self.assertEqual(["tile/chart", "tile/meter"], [child["definition"] for child in columns[0]["children"]])
        self.assertEqual(CHART_AND_METER_TOKENS, set(TOKEN_RE.findall(json.dumps(columns[0]))))
        outside = [child for child in root["children"] if child is not columns[0]]
        self.assertFalse(CHART_AND_METER_TOKENS & set(TOKEN_RE.findall(json.dumps(outside))))

    def test_schema_requirement_check_accepts_the_fully_hydrated_template(self):
        values = dict(SINGLE_DEAL_VALUES)
        values.update({
            "chartCaption": "Fixture", "chartCategories": ["Wk 1"], "chartSeries": [{"name": "Score", "data": [1]}],
            "meterLabel": "Fixture", "meterValue": 1, "meterMax": 100, "meterTarget": 70, "meterValueLabel": "1 / 100",
            "meterTargetLabel": "70", "meterStatus": "Cold", "meterBands": [{"from": 0, "to": 100, "variant": "error", "label": "Cold"}],
        })
        self.assertEqual([], schema_gaps(hydrate(renderer(), values)))

    def test_dropping_only_the_chart_and_meter_tokens_leaves_incomplete_tiles(self):
        widget = hydrate(renderer(), SINGLE_DEAL_VALUES)
        gaps = dict(schema_gaps(widget))

        self.assertEqual({"tile/chart", "tile/meter"}, set(gaps))
        self.assertTrue({"categories", "series", "caption"} <= set(gaps["tile/chart"]))
        self.assertTrue({"value", "valueLabel"} <= set(gaps["tile/meter"]))

    def test_single_deal_widget_without_the_column_is_complete(self):
        widget = without_chart_and_meter_column(hydrate(renderer(), SINGLE_DEAL_VALUES))
        found = definitions(widget)

        self.assertEqual([], schema_gaps(widget))
        self.assertNotIn("tile/chart", found)
        self.assertNotIn("tile/meter", found)
        self.assertIn("tile/datagrid", found)
        self.assertIn("tile/callout", found)
        self.assertNotRegex(json.dumps(widget), TOKEN_RE)


class DealSignalsStaleCommitmentTests(unittest.TestCase):
    def test_rule_follows_the_threshold_list(self):
        active = ACTIVE_SKILL.read_text()
        thresholds = section(active, "## 3. Check thresholds", "## 4. Widget")

        self.assertIn(local_paragraph(active, STALE_MARKER), thresholds)
        self.assertLess(thresholds.index("- **Stale commitment** — NextStep unchanged 21d+"), thresholds.index(STALE_MARKER))
        self.assertNotIn(STALE_MARKER, SOURCE_SKILL.read_text())

    def test_rule_reads_the_fetched_last_modified_date(self):
        active = ACTIVE_SKILL.read_text()
        rule = local_paragraph(active, STALE_MARKER)
        for required in (
            "when `<NEXTSTEP>` is set and `LastModifiedDate` is 21 or more days before today",
            "because no field on the deal has changed since then",
            "Fire Stale commitment for each such deal",
            "When `LastModifiedDate` is more recent, the record does not show the trigger, so do not fire it",
        ):
            self.assertIn(required, rule)
        self.assertIn("LastModifiedDate { value }", section(active, "## 2. Read the open book", "## 2b."))


class DealSignalsEmailEvidenceTests(unittest.TestCase):
    def test_rule_sits_with_the_evidence_step(self):
        active = ACTIVE_SKILL.read_text()
        evidence = section(active, "## 2b. Evidence", "## 3. Check thresholds")

        self.assertIn(local_paragraph(active, EMAIL_MARKER), evidence)
        self.assertLess(evidence.index(EMAIL_MARKER), evidence.index("**No extra Salesforce reads.**"))
        self.assertNotIn(EMAIL_MARKER, SOURCE_SKILL.read_text())

    def test_rule_requires_the_search_or_an_explicit_gap(self):
        rule = local_paragraph(ACTIVE_SKILL.read_text(), EMAIL_MARKER)
        for required in (
            "When an email tool is available, run the 2b email search for the flagged accounts",
            "it is part of the sweep, not optional",
            "add one line saying email was not checked",
            "so inbound-waiting, champion-risk, and competitor signals are not implied clear",
        ):
            self.assertIn(required, rule)


class DealSignalsCompleteDigestTests(unittest.TestCase):
    def test_rule_follows_the_digest_template(self):
        active = ACTIVE_SKILL.read_text()
        digest = active[active.index("## 5. Text — FALLBACK ONLY"):]

        self.assertEqual(1, active.count(DIGEST_MARKER))
        self.assertNotIn(DIGEST_MARKER, SOURCE_SKILL.read_text())
        self.assertLess(digest.index("✅ Nothing else crossed a threshold (<N> opps swept)\n```"), digest.index(DIGEST_MARKER))
        self.assertLess(digest.index("Link each record."), digest.index(DIGEST_MARKER))

    def test_rule_keeps_every_flagged_deal_and_the_closing_line(self):
        rule = local_paragraph(ACTIVE_SKILL.read_text(), DIGEST_MARKER)
        for required in (
            "List every deal that fired a signal, under its strongest signal",
            "lower-priority deals in the same group may share one line",
            "never drop a flagged deal to shorten the digest",
            "Always end with the ✅ line",
            "check that the number of deals listed equals the number that fired a signal",
        ):
            self.assertIn(required, rule)


if __name__ == "__main__":
    unittest.main()
