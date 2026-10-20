#!/usr/bin/env python3
"""Regression tests for extraction of documented Salesforce read calls."""

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("e2e_calls", HERE / "e2e_calls.py")
e2e_calls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e2e_calls)


class ConfigureLayoutExtractionTests(unittest.TestCase):
    def test_extracts_the_documented_layout_read(self):
        calls = e2e_calls.extract(["configure"])
        layout = [call for call in calls if call["kind"] == "layout"]
        self.assertEqual(1, len(layout))
        self.assertEqual("/services/data/v63.0/ui-api/records/<OPP_ID>", layout[0]["url"])
        self.assertEqual({"layoutTypes": "Full", "modes": "View"}, layout[0]["params"])

    def test_materializes_layout_read_with_a_typed_opportunity_id(self):
        layout = next(call for call in e2e_calls.extract(["configure"]) if call["kind"] == "layout")
        url, params, unresolved = e2e_calls.materialize(layout, e2e_calls.ID["OPP"])
        self.assertEqual(f"/services/data/v63.0/ui-api/records/{e2e_calls.ID['OPP']}", url)
        self.assertEqual({"layoutTypes": "Full", "modes": "View"}, params)
        self.assertEqual([], unresolved)

    def test_configure_layout_lookup_is_recognized(self):
        lookup = next(
            call for call in e2e_calls.extract(["configure"])
            if call["kind"] == "q" and "SELECT Id FROM Opportunity ORDER BY LastModifiedDate DESC LIMIT 1" in call["query"]
        )
        self.assertTrue(e2e_calls.is_configure_layout_lookup(lookup))


if __name__ == "__main__":
    unittest.main()
