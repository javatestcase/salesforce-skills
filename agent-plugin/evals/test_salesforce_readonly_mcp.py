#!/usr/bin/env python3
"""Offline route-policy tests for the local Salesforce read-only MCP adapter."""

import importlib.util
from importlib.machinery import SourceFileLoader
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "local-mcp" / "salesforce-readonly-mcp"
LOADER = SourceFileLoader("salesforce_readonly_mcp", str(SOURCE))
SPEC = importlib.util.spec_from_loader("salesforce_readonly_mcp", LOADER)
mcp = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(mcp)

OPPORTUNITY_ID = "006000000000000AAA"
LAYOUT_ARGS = {
    "method": "GET",
    "url": f"/services/data/v63.0/ui-api/records/{OPPORTUNITY_ID}",
    "queryParams": {"layoutTypes": "Full", "modes": "View"},
}


class OpportunityLayoutPolicyTests(unittest.TestCase):
    def test_allows_only_the_documented_full_view_layout_read(self):
        with mock.patch.object(mcp, "sf_rest", return_value={"fields": {"Name": {}}}) as sf_rest:
            text, is_error = mcp.call_tool("dispatch_readonly", LAYOUT_ARGS)
        self.assertFalse(is_error)
        self.assertIn('"fields"', text)
        sf_rest.assert_called_once_with(
            f"/services/data/v63.0/ui-api/records/{OPPORTUNITY_ID}?layoutTypes=Full&modes=View",
            "GET",
        )

    def test_rejects_near_miss_layout_requests_before_salesforce(self):
        invalid = [
            {**LAYOUT_ARGS, "method": "POST"},
            {**LAYOUT_ARGS, "url": f"/services/data/v64.0/ui-api/records/{OPPORTUNITY_ID}"},
            {**LAYOUT_ARGS, "url": "/services/data/v63.0/ui-api/records/001000000000000AAA"},
            {**LAYOUT_ARGS, "url": f"/services/data/v63.0/ui-api/records/{OPPORTUNITY_ID}/related"},
            {**LAYOUT_ARGS, "queryParams": {"layoutTypes": "Compact", "modes": "View"}},
            {**LAYOUT_ARGS, "queryParams": {"layoutTypes": "Full", "modes": "View", "extra": "no"}},
        ]
        with mock.patch.object(mcp, "sf_rest") as sf_rest:
            for args in invalid:
                with self.assertRaises(mcp.ToolError) as error:
                    mcp.call_tool("dispatch_readonly", args)
                self.assertIn("rejected", str(error.exception))
        sf_rest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
