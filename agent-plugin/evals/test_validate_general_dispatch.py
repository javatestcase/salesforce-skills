#!/usr/bin/env python3
"""Offline regression tests for the static general-dispatch guard."""

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("validate", HERE / "validate.py")
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


class GeneralDispatchGuardTests(unittest.TestCase):
    def test_rejects_direct_dispatch_calls(self):
        problems = validate.general_dispatch_call_problems('before\ndispatch(method: "POST", url: "/example")\nafter\n')
        self.assertEqual(["line 2: direct dispatch call is not allowed"], problems)

    def test_rejects_whitespace_before_call_parenthesis(self):
        problems = validate.general_dispatch_call_problems("dispatch (method: 'POST')")
        self.assertEqual(["line 1: direct dispatch call is not allowed"], problems)

    def test_allows_readonly_calls_and_widget_instructions(self):
        text = 'dispatch_readonly(method: "GET", url: "/query")\ndisplay_widget({ resourceType: "dynamic" })\n'
        self.assertEqual([], validate.general_dispatch_call_problems(text))


if __name__ == "__main__":
    unittest.main()
