#!/usr/bin/env python3
"""Regression tests for static validation of the documented Configure layout read."""

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("validate", HERE / "validate.py")
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


class LayoutReadValidationTests(unittest.TestCase):
    def test_accepts_the_documented_scalar_layout_read(self):
        text = '''dispatch_readonly(method: "GET", url: "/services/data/v63.0/ui-api/records/<OPP_ID>",
  queryParams: { "layoutTypes": "Full", "modes": "View" })
'''
        _, problems = validate.salesforce_call_problems(text)
        self.assertEqual([], problems)

    def test_rejects_invalid_scalar_layout_read_even_before_a_later_query(self):
        text = '''dispatch_readonly(method: "GET", url: "/services/data/v63.0/ui-api/records/<OPP_ID>",
  queryParams: { "layoutTypes": "Compact", "modes": "View" })
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\\"query\\":\\"query { uiapi { currentUser { Id } } }\\"}" })
'''
        _, problems = validate.salesforce_call_problems(text)
        self.assertEqual(1, len(problems))
        self.assertIn("line 1", problems[0])
        self.assertIn("no queryInput or q argument", problems[0])


if __name__ == "__main__":
    unittest.main()
