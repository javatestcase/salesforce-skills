#!/usr/bin/env python3
"""Render every active widget and capture its actions in an isolated MCP Apps shim.

The host and renderer use separate loopback origins. The renderer iframe is sandboxed with
``allow-scripts allow-same-origin``: it keeps its own non-opaque origin while remaining
cross-origin from the host. Widget actions are captured as MCP Apps requests and acknowledged;
the harness never sends a message, opens a link, or writes Salesforce data.
"""

import argparse
import collections
import functools
import html
import json
import re
import shutil
import struct
import subprocess
import tempfile
import threading
import urllib.parse
import zlib
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from active_widget_browser_inputs import browser_inputs

HERE = Path(__file__).resolve().parent
CAPTURE_ROOT = HERE / "captures"
DEFAULT_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
CAPTURES = HERE / "host_captures"

REPORTER = """<script>
let shimActionsClicked = false;
window.addEventListener("message", event => {
  const message = event.data;
  if (!message || message.type !== "shim/click-action-labels" || shimActionsClicked) return;
  shimActionsClicked = true;
  const buttons = [...document.querySelectorAll("button:not([disabled])")];
  const used = new Set();
  const missing = [];
  let count = 0;
  for (const label of message.labels || []) {
    const index = buttons.findIndex((button, candidate) =>
      !used.has(candidate) && button.textContent.trim() === label);
    if (index < 0) { missing.push(label); continue; }
    used.add(index);
    count += 1;
    buttons[index].dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true, view: window}));
  }
  window.parent.postMessage({type:"shim/action-clicks", count, missing}, "*");
});
function shimRenderState() {
  const text = document.body?.innerText || "";
  const trimmed = text.trim();
  const state = trimmed.includes("Initializing") ? "initializing" :
    trimmed.includes("Waiting for view") ? "waiting" :
    trimmed === "Loading…" || trimmed === "Loading..." ? "loading" :
    trimmed ? "rendered" : "empty";
  const root = document.getElementById("root");
  const rect = root?.getBoundingClientRect();
  window.parent.postMessage({
    type: "shim/render-state",
    state,
    text,
    rootBox: rect ? {width: rect.width, height: rect.height} : null
  }, "*");
}
setInterval(shimRenderState, 200);
</script>"""

HOST_TEMPLATE = """<!doctype html>
<html lang="en" data-shim-state="starting">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__SKILL__ MCP Apps cross-origin test</title>
<style>html,body{margin:0;background:#fff;font:14px system-ui}iframe{display:block;width:100%;height:1100px;border:0}#status{padding:8px 12px;background:#eef3f8}</style>
</head>
<body>
<div id="status">Starting __SKILL__…</div><iframe id="app" sandbox="allow-scripts allow-same-origin"></iframe>
<script>
const toolInput = __TOOL_INPUT__;
const toolResult = __TOOL_RESULT__;
const expectedText = __EXPECTED_TEXT__;
const expectedActionLabels = __ACTION_LABELS__;
const app = document.getElementById("app");
const status = document.getElementById("status");
const events = [];
const messages = [];
const links = [];
let deliveries = 0;
let initializedCount = 0;
let actionClicks = 0;
let missingActionLabels = [];
let actionRequestSent = false;
let renderState = "starting";
let renderText = "";
let rootBox = null;
function send(message) { app.contentWindow.postMessage(message, "*"); }
function respond(message, result = {}) { send({jsonrpc:"2.0", id:message.id, result}); }
function deliver() {
  deliveries += 1;
  send({jsonrpc:"2.0", method:"ui/notifications/tool-input", params:{arguments:toolInput}});
  send({jsonrpc:"2.0", method:"ui/notifications/tool-result", params:toolResult});
}
window.addEventListener("message", event => {
  if (event.source !== app.contentWindow || !event.data || typeof event.data !== "object") return;
  const message = event.data;
  if (message.type === "shim/render-state") {
    renderState = message.state; renderText = message.text; rootBox = message.rootBox;
    if (renderState === "rendered" && !actionRequestSent) {
      actionRequestSent = true;
      setTimeout(() => send({type:"shim/click-action-labels", labels:expectedActionLabels}), 200);
    }
    return;
  }
  if (message.type === "shim/action-clicks") {
    actionClicks = message.count; missingActionLabels = message.missing || []; return;
  }
  events.push(message.method || ("response:" + message.id));
  if (message.method === "ui/initialize" && message.id !== undefined) {
    respond(message, {
      protocolVersion:"2026-01-26",
      hostInfo:{name:"salesforce-renderer-shim",version:"0.1.0"},
      hostCapabilities:{},
      hostContext:{theme:"light",displayMode:"inline",locale:"en-US",timeZone:"UTC",platform:"web",
        toolInfo:{name:"display_widget",_meta:toolResult._meta}}
    });
  } else if (message.method === "ui/notifications/initialized") {
    initializedCount += 1;
    if (initializedCount === 1) deliver();
  } else if (message.method === "ui/notifications/size-changed") {
    const height = Number(message.params?.height);
    if (Number.isFinite(height) && height > 0) app.style.height = `${Math.ceil(height)}px`;
  } else if (message.method === "ui/message") {
    messages.push(message.params || {}); if (message.id !== undefined) respond(message);
  } else if (message.method === "ui/open-link") {
    links.push(message.params || {}); if (message.id !== undefined) respond(message);
  } else if (message.id !== undefined && message.method) {
    respond(message);
  }
});
function publishDiagnostics() {
  const textChecks = expectedText.map(value => renderText.includes(value));
  document.documentElement.dataset.shimState = renderState;
  document.documentElement.dataset.shimText = encodeURIComponent(renderText);
  document.documentElement.dataset.shimTextChecks = encodeURIComponent(JSON.stringify(textChecks));
  document.documentElement.dataset.shimRootBox = encodeURIComponent(JSON.stringify(rootBox));
  document.documentElement.dataset.shimDeliveries = String(deliveries);
  document.documentElement.dataset.shimActionClicks = String(actionClicks);
  document.documentElement.dataset.shimMissingActionLabels = encodeURIComponent(JSON.stringify(missingActionLabels));
  document.documentElement.dataset.shimMessages = encodeURIComponent(JSON.stringify(messages));
  document.documentElement.dataset.shimLinks = encodeURIComponent(JSON.stringify(links));
  document.documentElement.dataset.shimEvents = encodeURIComponent(JSON.stringify(events));
  status.textContent = `__SKILL__: ${renderState} · deliveries ${deliveries} · actions ${actionClicks}`;
}
setInterval(publishDiagnostics, 200);
app.src = __CHILD_URL__;
</script>
</body></html>"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        return


def javascript(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


def renderer_with_reporter(path):
    renderer = path.read_text()
    body_end = renderer.rfind("</body>")
    if body_end < 0:
        raise RuntimeError(f"renderer has no outer </body>: {path}")
    return renderer[:body_end] + REPORTER + renderer[body_end:]


def host_document(item, child_url):
    widget = item["widget"]
    tool_input = {"resourceType": "dynamic", "widgetDefinition": widget}
    tool_result = {
        "content": [{"type": "text", "text": f"{item['skill']} deterministic widget result"}],
        "structuredContent": {"widgetDefinition": widget},
        "_meta": {
            "salesforce/uiMetadata": widget,
            "ui": {"resourceUri": "ui://widget/salesforce-widget-renderer"},
        },
        "isError": False,
    }
    return (HOST_TEMPLATE
            .replace("__SKILL__", item["skill"])
            .replace("__TOOL_INPUT__", javascript(tool_input))
            .replace("__TOOL_RESULT__", javascript(tool_result))
            .replace("__EXPECTED_TEXT__", javascript(item["expectedText"]))
            .replace("__ACTION_LABELS__", javascript(item["expectedActionLabels"]))
            .replace("__CHILD_URL__", javascript(child_url)))


def attribute(document, name, default=None):
    match = re.search(rf'data-{re.escape(name)}="([^"]*)"', document)
    return default if not match else urllib.parse.unquote(html.unescape(match.group(1)))


def json_attribute(document, name, default):
    value = attribute(document, name)
    return default if value is None else json.loads(value)


def paeth(left, above, upper_left):
    estimate = left + above - upper_left
    distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
    return (left, above, upper_left)[distances.index(min(distances))]


def screenshot_pixels(path, top=40):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"not a PNG: {path}")
    cursor, compressed, width, height, color_type = 8, bytearray(), None, None, None
    while cursor < len(data):
        length = struct.unpack(">I", data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        payload = data[cursor + 8:cursor + 8 + length]
        cursor += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", payload)
            if bit_depth != 8 or interlace != 0 or color_type not in {2, 6}:
                raise RuntimeError(f"unsupported PNG format: depth={bit_depth}, color={color_type}, interlace={interlace}")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    decoded = zlib.decompress(compressed)
    previous = bytearray(stride)
    offset, non_white = 0, 0
    for y in range(height):
        filter_type = decoded[offset]
        source = decoded[offset + 1:offset + 1 + stride]
        offset += 1 + stride
        row = bytearray(stride)
        for index, value in enumerate(source):
            left = row[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                result = value
            elif filter_type == 1:
                result = value + left
            elif filter_type == 2:
                result = value + above
            elif filter_type == 3:
                result = value + ((left + above) // 2)
            elif filter_type == 4:
                result = value + paeth(left, above, upper_left)
            else:
                raise RuntimeError(f"unsupported PNG filter {filter_type}")
            row[index] = result & 0xFF
        if y >= top:
            for x in range(width):
                pixel = x * channels
                alpha = row[pixel + 3] if channels == 4 else 255
                if alpha and min(row[pixel:pixel + 3]) < 245:
                    non_white += 1
        previous = row
    return {"width": width, "height": height, "nonWhitePixelsBelowHeader": non_white}


def message_text(params):
    content = params.get("content") if isinstance(params, dict) else None
    if not isinstance(content, list):
        return ""
    return "".join(block.get("text", "") for block in content
                   if isinstance(block, dict) and block.get("type") == "text")


def run_browser(chrome, url, screenshot, timeout):
    profile = Path(tempfile.mkdtemp(prefix="salesforce-mcp-apps-chrome-", dir="/private/tmp"))
    command = [
        str(chrome), "--headless=new", "--disable-gpu", "--disable-background-networking",
        "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}",
        "--window-size=1440,1200", "--virtual-time-budget=15000",
        "--run-all-compositor-stages-before-draw",
        "--host-resolver-rules=MAP * 0.0.0.0, EXCLUDE 127.0.0.1",
        f"--screenshot={screenshot}", "--dump-dom", url,
    ]
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def evaluate(item, process, screenshot):
    document = process.stdout
    expected_messages = item["expectedMessages"]
    expected_links = item["expectedLinks"]
    actual_messages = [message_text(value) for value in json_attribute(document, "shim-messages", [])]
    actual_links = [value.get("url", "") for value in json_attribute(document, "shim-links", [])
                    if isinstance(value, dict)]
    text_checks = json_attribute(document, "shim-text-checks", [])
    root_box = json_attribute(document, "shim-root-box", None)
    events = json_attribute(document, "shim-events", [])
    clicked = int(attribute(document, "shim-action-clicks", "0"))
    missing_action_labels = json_attribute(document, "shim-missing-action-labels", [])
    deliveries = int(attribute(document, "shim-deliveries", "0"))
    state = attribute(document, "shim-state", "missing")
    pixels = screenshot_pixels(screenshot) if screenshot.is_file() else None
    checks = [
        {"name": "Chrome completed", "ok": process.returncode == 0},
        {"name": "renderer reached rendered state", "ok": state == "rendered"},
        *[
            {"name": f"visible text: {text}", "ok": index < len(text_checks) and text_checks[index]}
            for index, text in enumerate(item["expectedText"])
        ],
        {"name": "renderer has visible geometry", "ok": bool(root_box and root_box.get("width", 0) >= 300 and root_box.get("height", 0) >= 40)},
        {"name": "screenshot contains painted widget pixels", "ok": bool(pixels and pixels["nonWhitePixelsBelowHeader"] >= 500)},
        {"name": "one tool state delivery", "ok": deliveries == 1},
        {"name": "all declared actions have rendered targets", "ok": not missing_action_labels and clicked == len(item["expectedActionLabels"])},
        {"name": "sendMessage requests match declarations", "ok": collections.Counter(actual_messages) == collections.Counter(expected_messages)},
        {"name": "openLink requests match declarations", "ok": collections.Counter(actual_links) == collections.Counter(expected_links)},
    ]
    return {
        "skill": item["skill"],
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
        "state": state,
        "rootBox": root_box,
        "pixels": pixels,
        "expectedText": item["expectedText"],
        "expectedMessages": expected_messages,
        "actualMessages": actual_messages,
        "expectedLinks": expected_links,
        "actualLinks": actual_links,
        "expectedActionLabels": item["expectedActionLabels"],
        "missingActionLabels": missing_action_labels,
        "clickedActionTargets": clicked,
        "events": events,
        "chromeStderr": process.stderr[-1000:] if process.returncode else "",
    }


def latest_renderer():
    candidates = sorted(CAPTURE_ROOT.glob("*/widget-0.raw.html"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise SystemExit(
            "no captured renderer HTML; run evals/mcp_apps/h360_display_widget_capture.py first "
            "or pass --renderer-html"
        )
    return candidates[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", help="optional active widget skill names")
    parser.add_argument("--chrome", type=Path, default=DEFAULT_CHROME)
    parser.add_argument("--renderer-html", type=Path)
    parser.add_argument("--timeout", type=int, default=90, help="seconds per Chrome run")
    args = parser.parse_args()
    renderer_html = args.renderer_html or latest_renderer()
    if not args.chrome.is_file():
        raise SystemExit(f"Chrome not found: {args.chrome}")
    if not renderer_html.is_file():
        raise SystemExit(f"renderer HTML not found: {renderer_html}")

    generated = browser_inputs()
    selected = generated["widgets"]
    if args.skills:
        requested = set(args.skills)
        selected = [item for item in selected if item["skill"] in requested]
        missing = sorted(requested - {item["skill"] for item in selected})
        if missing:
            raise SystemExit(f"no active dynamic widget for: {', '.join(missing)}")

    capture_dir = CAPTURES / (datetime.now(timezone.utc).strftime("shim-suite-%Y%m%dT%H%M%SZ"))
    capture_dir.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="salesforce-mcp-apps-shim-", dir="/private/tmp") as temporary:
        web_root = Path(temporary)
        (web_root / "renderer.html").write_text(renderer_with_reporter(renderer_html))
        handler = functools.partial(QuietHandler, directory=str(web_root))
        host_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        child_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threads = [threading.Thread(target=server.serve_forever, daemon=True)
                   for server in (host_server, child_server)]
        for thread in threads:
            thread.start()
        host_port = host_server.server_address[1]
        child_port = child_server.server_address[1]
        child_url = f"http://127.0.0.1:{child_port}/renderer.html?actions=1"
        results = []
        try:
            for item in selected:
                print(f"Testing {item['skill']}...", flush=True)
                filename = f"{item['skill']}.html"
                (web_root / filename).write_text(host_document(item, child_url))
                screenshot = capture_dir / f"{item['skill']}.png"
                process = run_browser(
                    args.chrome,
                    f"http://127.0.0.1:{host_port}/{filename}",
                    screenshot,
                    args.timeout,
                )
                result = evaluate(item, process, screenshot)
                results.append(result)
                failed = [check["name"] for check in result["checks"] if not check["ok"]]
                print(f"  {'PASS' if result['ok'] else 'FAIL'}" + (f": {', '.join(failed)}" if failed else ""), flush=True)
        finally:
            host_server.shutdown()
            child_server.shutdown()
            host_server.server_close()
            child_server.server_close()

    summary = {
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "scenario": generated["scenario"],
        "rendererHtml": str(renderer_html),
        "hostPolicy": "capture-only; separate loopback origins; no sends, links, or Salesforce writes",
        "tested": len(results),
        "skipped": generated["skipped"] if not args.skills else [],
        "passed": [result["skill"] for result in results if result["ok"]],
        "failed": [result["skill"] for result in results if not result["ok"]],
        "results": results,
    }
    summary["ok"] = not summary["failed"]
    (capture_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({
        "captureDir": str(capture_dir),
        "tested": summary["tested"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "ok": summary["ok"],
    }, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
