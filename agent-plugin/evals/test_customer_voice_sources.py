#!/usr/bin/env python3
"""Deterministic local checks for the customer-voice Quick/Kiro adaptation."""

import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent
ACTIVE_SKILL = PLUGIN_ROOT / "skills" / "customer-voice" / "SKILL.md"
SOURCE_SKILL = PLUGIN_ROOT.parent / "salesforce-for-sales" / "skills" / "customer-voice" / "SKILL.md"
EVAL_SPEC = HERE / "skills" / "customer-voice" / "eval.yaml"
SOURCES_MARKER = "**Sources — Quick/Kiro adaptation:**"
NO_QUOTES_MARKER = "**No quotes found — Quick/Kiro adaptation:**"


def local_paragraph(text, marker):
    """Return the single-line local paragraph that starts with ``marker``."""
    start = text.index(marker)
    return text[start:text.index("\n", start)]


class CustomerVoiceSourceTests(unittest.TestCase):
    def setUp(self):
        self.active = ACTIVE_SKILL.read_text()
        self.source = SOURCE_SKILL.read_text()

    def test_rules_are_active_only_and_sit_at_their_decision_points(self):
        for marker in (SOURCES_MARKER, NO_QUOTES_MARKER):
            self.assertEqual(1, self.active.count(marker))
            self.assertNotIn(marker, self.source)

        # The source rule belongs with the searches; the zero-quote rule follows the output template.
        sources_rule = self.active.index(SOURCES_MARKER)
        self.assertLess(self.active.index("## 2. Search sources"), sources_rule)
        self.assertLess(sources_rule, self.active.index("## 3. Extract quotes"))
        template_end = self.active.index("- Topic not mentioned in: <accounts>\n```\n")
        self.assertLess(template_end, self.active.index(NO_QUOTES_MARKER))

    def test_salesforce_stays_limited_to_the_three_scoping_reads(self):
        rule = local_paragraph(self.active, SOURCES_MARKER)
        for required in (
            "Quotes come only from these docs and email searches",
            "make no Salesforce reads beyond the three in step 1",
            "never search Tasks, Events, Cases, or other records as a substitute source",
            "report no counts from such a search",
        ):
            self.assertIn(required, rule)

        context = self.active[self.active.index("## 1. Context"):self.active.index("## 2. Search sources")]
        self.assertEqual(3, context.count("dispatch_readonly("))
        self.assertRegex(EVAL_SPEC.read_text(), r"(?m)^\s*max_salesforce_reads: 3\b")

    def test_zero_quote_output_keeps_the_template(self):
        rule = local_paragraph(self.active, NO_QUOTES_MARKER)
        for required in (
            "still return this template with 0 quotes",
            "keeping the topic and period in the header",
            "Write `None` under Accounts represented and fill Gaps as shown",
            "at most one line offering a wider period or scope",
            "offer no other source",
        ):
            self.assertIn(required, rule)

    def test_active_skill_differs_from_source_only_by_the_local_rules(self):
        reduced = self.active
        for marker in (SOURCES_MARKER, NO_QUOTES_MARKER):
            reduced = reduced.replace("\n" + local_paragraph(reduced, marker) + "\n", "", 1)
        self.assertEqual(self.source, reduced)


if __name__ == "__main__":
    unittest.main()
