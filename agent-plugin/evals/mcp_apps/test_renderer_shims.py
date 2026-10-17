#!/usr/bin/env python3
"""Offline clean-checkout tests for the explicit renderer-input shim generators."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class RendererShimTests(unittest.TestCase):
    def test_generators_accept_a_supplied_renderer_and_create_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            renderer = root / "renderer.html"
            renderer.write_text("<!doctype html><html><head></head><body>fixture renderer</body></html>")
            mcp_output = root / "mcp"
            openai_output = root / "openai.html"

            mcp = subprocess.run(
                [sys.executable, str(HERE / "renderer_mcp_apps_shim.py"),
                 "--renderer-html", str(renderer), "--output-dir", str(mcp_output)],
                cwd=HERE,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, mcp.returncode, mcp.stderr)
            self.assertIn("mcp-apps-host-shim.html", mcp.stdout)
            self.assertIn("shim/render-state", (mcp_output / "mcp-apps-shim-renderer.html").read_text())
            self.assertIn("ui/notifications/tool-result", (mcp_output / "mcp-apps-host-shim.html").read_text())

            openai = subprocess.run(
                [sys.executable, str(HERE / "renderer_openai_shim.py"),
                 "--renderer-html", str(renderer), "--output", str(openai_output)],
                cwd=HERE,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, openai.returncode, openai.stderr)
            self.assertIn("window.openai", openai_output.read_text())

    def test_generators_require_a_renderer_input(self):
        for script in ("renderer_mcp_apps_shim.py", "renderer_openai_shim.py"):
            result = subprocess.run(
                [sys.executable, str(HERE / script)],
                cwd=HERE,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("--renderer-html", result.stderr)


if __name__ == "__main__":
    unittest.main()
