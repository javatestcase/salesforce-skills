#!/usr/bin/env python3
"""Generate a test-only parent-frame MCP Apps host for a supplied renderer HTML file."""

import argparse
import json
from pathlib import Path

from active_widget_templates import assert_active_widget_parity
from account_context_widget_capture import hydrate

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = HERE / "host_captures"


def javascript(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer-html", type=Path, required=True,
                        help="captured Salesforce renderer HTML; intentionally not tracked in this repository")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="directory for generated shim files (default: ignored host_captures/)")
    args = parser.parse_args(argv)
    if not args.renderer_html.is_file():
        parser.error(f"renderer HTML does not exist: {args.renderer_html}")
    return args


def main(argv=None):
    args = parse_args(argv)
    fixture = json.loads((HERE / "fixtures" / "account-context.json").read_text())
    template = assert_active_widget_parity("account-context")
    if template is None:
        raise SystemExit("active account-context skill has no dynamic widget")
    widget = hydrate(template, fixture["values"])
    tool_input = {"resourceType": "dynamic", "widgetDefinition": widget}
    tool_result = {
        "content": [{"type": "text", "text": "Ravelin Rail Logistics widget shim result"}],
        "structuredContent": {"widgetDefinition": widget},
        "_meta": {
            "salesforce/uiMetadata": widget,
            "ui": {"resourceUri": "ui://widget/salesforce-widget-renderer"},
        },
        "isError": False,
    }

    renderer = args.renderer_html.read_text()
    if "<head" not in renderer.lower() or "</body>" not in renderer.lower():
        raise SystemExit(f"renderer must contain outer <head> and </body> elements: {args.renderer_html}")
    output_dir = args.output_dir
    child = output_dir / "mcp-apps-shim-renderer.html"
    host = output_dir / "mcp-apps-host-shim.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    reporter = """<script>
function reportShimRenderState() {
  const text = document.body?.innerText || "";
  const state = text.includes("Ravelin Rail Logistics") ? "rendered" :
    text.includes("Initializing") ? "initializing" :
    text.includes("Loading") ? "loading" :
    text.includes("Waiting for view") ? "waiting" : "other";
  window.parent.postMessage({type:"shim/render-state",state,textLength:text.length}, "*");
}
setInterval(reportShimRenderState, 200);
</script>"""
    body_end = renderer.lower().rfind("</body>")
    child.write_text(renderer[:body_end] + reporter + renderer[body_end:])

    host.write_text(f"""<!doctype html>
<html lang="en" data-shim-state="starting">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCP Apps renderer compatibility shim</title>
<style>html,body{{margin:0;background:#fff;font:14px system-ui}}iframe{{display:block;width:100%;height:1100px;border:0}}#status{{padding:8px 12px;background:#eef3f8}}#log{{display:none}}</style>
</head>
<body>
<div id="status">Starting MCP Apps host shim…</div>
<iframe id="app"></iframe><pre id="log"></pre>
<script>
const toolInput = {javascript(tool_input)};
const toolResult = {javascript(tool_result)};
const app = document.getElementById("app");
const status = document.getElementById("status");
const parameters = new URLSearchParams(window.location.search);
const mode = parameters.get("mode") || "repeat";
const childUrl = parameters.get("child") || "mcp-apps-shim-renderer.html";
const sandboxMode = parameters.get("sandbox") || "0";
const sandboxed = sandboxMode !== "0";
if (sandboxMode === "opaque") app.setAttribute("sandbox", "allow-scripts allow-forms allow-popups");
if (sandboxMode === "same-origin") app.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups");
const events = [];
let deliveries = 0;
let initializedCount = 0;
let reportedState = "starting";
let reportedTextLength = 0;
function send(message) {{ app.contentWindow.postMessage(message, "*"); }}
function deliver() {{
  deliveries += 1;
  send({{jsonrpc:"2.0",method:"ui/notifications/tool-input",params:{{arguments:toolInput}}}});
  send({{jsonrpc:"2.0",method:"ui/notifications/tool-result",params:toolResult}});
}}
window.addEventListener("message", event => {{
  if (event.source !== app.contentWindow || !event.data || typeof event.data !== "object") return;
  const message = event.data;
  if (message.type === "shim/render-state") {{
    reportedState = message.state;
    reportedTextLength = message.textLength;
    return;
  }}
  events.push(message.method || ("response:" + message.id));
  if (message.method === "ui/initialize" && message.id !== undefined) {{
    send({{jsonrpc:"2.0",id:message.id,result:{{
      protocolVersion:"2026-01-26",
      hostInfo:{{name:"salesforce-renderer-shim",version:"0.1.0"}},
      hostCapabilities:{{}},
      hostContext:{{
        theme:"light",displayMode:"inline",locale:"en-US",timeZone:"UTC",platform:"web",
        toolInfo:{{name:"display_widget",_meta:toolResult._meta}}
      }}
    }}}});
  }} else if (message.method === "ui/notifications/initialized") {{
    initializedCount += 1;
    if (mode === "first" && initializedCount === 1) deliver();
    if (mode === "each") deliver();
    if (mode === "repeat") {{ deliver(); setTimeout(deliver, 250); setTimeout(deliver, 1000); }}
  }} else if (message.method === "ui/notifications/size-changed") {{
    const height = Number(message.params?.height);
    if (Number.isFinite(height) && height > 0) app.style.height = `${{Math.ceil(height)}}px`;
  }} else if (message.id !== undefined && message.method) {{
    send({{jsonrpc:"2.0",id:message.id,result:{{}}}});
  }}
}});
function inspect() {{
  let text = "";
  if (!sandboxed) {{
    try {{ text = app.contentDocument?.body?.innerText || ""; }} catch (error) {{ events.push("inspect-error:" + error); }}
  }}
  const directState = text.includes("Ravelin Rail Logistics") ? "rendered" :
    text.includes("Initializing") ? "initializing" :
    text.includes("Loading") ? "loading" :
    text.includes("Waiting for view") ? "waiting" : "other";
  const state = sandboxed ? reportedState : directState;
  const textLength = sandboxed ? reportedTextLength : text.length;
  document.documentElement.dataset.shimState = state;
  document.documentElement.dataset.shimTextLength = String(textLength);
  document.documentElement.dataset.shimDeliveries = String(deliveries);
  document.documentElement.dataset.shimSandboxed = String(sandboxed);
  document.documentElement.dataset.shimEvents = encodeURIComponent(JSON.stringify(events));
  status.textContent = `MCP Apps shim: ${{state}} · sandbox ${{sandboxed}} · deliveries ${{deliveries}}`;
}}
setInterval(inspect, 200);
app.src = childUrl;
</script>
</body></html>""")
    print(json.dumps({"host": str(host), "renderer": str(child), "widgetRoot": widget["renderer"]["componentOverrides"]["$"]["definition"]}, indent=2))


if __name__ == "__main__":
    main()
