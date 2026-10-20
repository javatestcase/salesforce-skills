#!/usr/bin/env python3
"""Deterministic local Quick/Kiro reconciliation checks for account-tiering."""

import unittest
from collections import Counter
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "account-tiering" / "SKILL.md"


def tier(raw_fit, raw_engagement):
    if raw_fit >= 6 and raw_engagement >= 6:
        return "Tier A"
    if raw_fit >= 6:
        return "Tier B"
    if raw_engagement >= 6:
        return "Tier C"
    return "Deprioritize"


def heatmap_cell(raw_fit, raw_engagement):
    return (
        "High (6–10)" if raw_engagement >= 6 else "Low (0–5)",
        "High fit (6–10)" if raw_fit >= 6 else "Low fit (0–5)",
    )


class AccountTieringReconciliationTests(unittest.TestCase):
    def test_binary_heatmap_reconciles_with_tiers(self):
        scores = [(10, 6)] + [(7, 5)] * 10
        tiers = Counter(tier(fit, engagement) for fit, engagement in scores)
        cells = Counter(heatmap_cell(fit, engagement) for fit, engagement in scores)

        self.assertEqual({"Tier A": 1, "Tier B": 10}, dict(tiers))
        self.assertEqual(1, cells[("High (6–10)", "High fit (6–10)")])
        self.assertEqual(10, cells[("Low (0–5)", "High fit (6–10)")])
        self.assertEqual(0, cells[("High (6–10)", "Low fit (0–5)")])
        self.assertEqual(0, cells[("Low (0–5)", "Low fit (0–5)")])
        self.assertEqual(len(scores), sum(cells.values()))

    def test_display_conversions_do_not_change_raw_classification(self):
        raw_fit, raw_engagement = 7, 6
        self.assertEqual("Tier A", tier(raw_fit, raw_engagement))
        self.assertEqual(("High (6–10)", "High fit (6–10)"), heatmap_cell(raw_fit, raw_engagement))
        self.assertEqual(3.5, raw_fit / 2)
        self.assertEqual(60, raw_engagement * 10)

    def test_active_skill_declares_binary_reconciliation(self):
        text = SKILL.read_text()
        for required in (
            "**Quick/Kiro tier-display reconciliation — local adaptation:**",
            '`heatmapXLabels` is exactly\n  `["Low (0–5)", "High (6–10)"]`',
            '`heatmapYLabels` is exactly\n  `["High fit (6–10)", "Low fit (0–5)"]`',
            "High-fit/High-engagement count MUST equal Tier A",
            "never create\n  a Mid fit or Mid engagement band",
            "raw Fit ÷ 2",
            "raw Engagement × 10",
        ):
            self.assertIn(required, text)

    def test_active_skill_forbids_zero_defaults_for_unavailable_metrics(self):
        text = SKILL.read_text()
        for required in (
            "standard `AnnualRevenue` is not\n  ARR",
            "a picklist such as Upsell Opportunity is not a whitespace amount",
            "omit that row key and\n  its corresponding datagrid column",
            "Never substitute `0`, `$0`, or `$0.00` for unavailable data",
            "render only Account, ICP fit, Engagement, and Motion columns",
        ):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()
