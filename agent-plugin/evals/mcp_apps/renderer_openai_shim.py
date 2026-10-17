#!/usr/bin/env python3
"""Generate a test-only OpenAI-host shim around supplied renderer HTML."""

import argparse
import json
from pathlib import Path

from active_widget_templates import assert_active_widget_parity
from account_context_widget_capture import hydrate

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "host_captures" / "openai-host-shim.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer-html", type=Path, required=True,
                        help="captured Salesforce renderer HTML; intentionally not tracked in this repository")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.renderer_html.is_file():
        parser.error(f"renderer HTML does not exist: {args.renderer_html}")

    fixture = json.loads((HERE / "fixtures" / "account-context.json").read_text())
    template = assert_active_widget_parity("account-context")
    if template is None:
        raise SystemExit("active account-context skill has no dynamic widget")
    widget = hydrate(template, fixture["values"])
    tool_input = {"resourceType": "dynamic", "widgetDefinition": widget}
    tool_output = {"widgetDefinition": widget}
    tool_metadata = {
        "salesforce/uiMetadata": widget,
        "openai/outputTemplate": "ui://widget/salesforce-widget-renderer",
    }

    def javascript(value):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")

    shim = f"""<script>
window.__shimErrors = [];
window.addEventListener("error", event => window.__shimErrors.push(String(event.error?.stack || event.message)));
window.addEventListener("unhandledrejection", event => window.__shimErrors.push(String(event.reason?.stack || event.reason)));
window.openai = {{
  theme: "light",
  locale: "en-US",
  displayMode: "inline",
  maxHeight: 1200,
  safeAreaInsets: {{ top: 0, right: 0, bottom: 0, left: 0 }},
  toolInput: {javascript(tool_input)},
  toolOutput: {javascript(tool_output)},
  toolResponseMetadata: {javascript(tool_metadata)},
  widgetState: null,
  setWidgetState(value) {{ this.widgetState = value; window.dispatchEvent(new Event("openai:set_globals")); }},
  sendFollowUpMessage(message) {{ window.__shimLastMessage = message; return Promise.resolve({{}}); }},
  callTool(name, params) {{ window.__shimLastTool = {{ name, params }}; return Promise.resolve({{}}); }},
  openExternal(request) {{ window.__shimLastLink = request; return Promise.resolve({{}}); }},
  requestDisplayMode(request) {{ this.displayMode = request.mode; return Promise.resolve({{ mode: request.mode }}); }},
  requestModal() {{ return Promise.resolve({{}}); }}
}};
function updateShimDiagnostics() {{
  const text = document.body?.innerText || "";
  const state = text.includes("Ravelin Rail Logistics") ? "rendered" :
    text.includes("Initializing") ? "initializing" :
    text.includes("Waiting for view") ? "waiting" : "other";
  document.documentElement.dataset.shimState = state;
  document.documentElement.dataset.shimTextLength = String(text.length);
  document.documentElement.dataset.shimErrorCount = String(window.__shimErrors.length);
  document.documentElement.dataset.shimErrors = encodeURIComponent(JSON.stringify(window.__shimErrors));
}}
setInterval(updateShimDiagnostics, 250);
</script>"""

    renderer = args.renderer_html.read_text()
    if "<head" not in renderer.lower():
        raise SystemExit(f"renderer has no <head>: {args.renderer_html}")
    output = renderer.replace("<head>", "<head>" + shim, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output)
    print(json.dumps({
        "output": str(args.output),
        "active_skill": "skills/account-context/SKILL.md",
        "renderer": str(args.renderer_html),
        "widget_root": widget["renderer"]["componentOverrides"]["$"]["definition"],
    }, indent=2))


if __name__ == "__main__":
    main()
