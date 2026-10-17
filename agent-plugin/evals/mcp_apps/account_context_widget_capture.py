#!/usr/bin/env python3
"""Capture and validate the active account-context Headless 360 widget contract.

The test proves the active template/variable-contract blocks match upstream, then hydrates that
active renderer with deterministic fixture values, submits it to hosted Headless 360, and
validates the raw MCP response. OAuth credentials remain in memory; raw captures are redacted.
"""

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from active_widget_templates import WidgetTemplateError, assert_active_widget_parity

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "h360_display_widget_capture.py"
spec = importlib.util.spec_from_file_location("h360_capture", BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
ROOT = HERE.parents[1]
REPO_ROOT = ROOT.parent
TOKEN_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


def hydrate(value, values):
    if isinstance(value, str):
        exact = TOKEN_RE.fullmatch(value)
        if exact:
            key = exact.group(1)
            if key not in values:
                raise base.ProbeError(f"missing fixture value for {key}")
            return values[key]
        return TOKEN_RE.sub(lambda match: str(values[match.group(1)]), value)
    if isinstance(value, list):
        return [hydrate(item, values) for item in value]
    if isinstance(value, dict):
        return {key: hydrate(item, values) for key, item in value.items()}
    return value


def walk(value, definitions, actions, strings):
    if isinstance(value, dict):
        if isinstance(value.get("definition"), str):
            definitions.append(value["definition"])
            if value["definition"].startswith("action/"):
                actions.append(value)
        for item in value.values():
            walk(item, definitions, actions, strings)
    elif isinstance(value, list):
        for item in value:
            walk(item, definitions, actions, strings)
    elif isinstance(value, str):
        strings.append(value)


def validate_account_widget(result, submitted, expected, capture_dir):
    structured = result.get("structuredContent", {}).get("widgetDefinition")
    metadata = result.get("_meta", {}).get("salesforce/uiMetadata")
    checks = []
    checks.append({"name": "structuredContent widgetDefinition", "ok": isinstance(structured, dict)})
    checks.append({"name": "salesforce/uiMetadata", "ok": isinstance(metadata, dict)})
    checks.append({"name": "structured widget equals active submitted widget", "ok": structured == submitted})
    checks.append({"name": "metadata equals active submitted widget", "ok": metadata == submitted})
    checks.append({"name": "metadata equals structured widget", "ok": structured == metadata})
    widget = structured if isinstance(structured, dict) else {}
    base.write_json(capture_dir / "account-context.widget-definition.json", widget)
    root = widget.get("renderer", {}).get("componentOverrides", {}).get("$", {})
    checks.append({"name": "tile/widget root", "ok": root.get("definition") == "tile/widget"})
    definitions, actions, strings = [], [], []
    walk(widget, definitions, actions, strings)
    for definition in expected["required_definitions"]:
        checks.append({"name": f"required definition: {definition}", "ok": definition in definitions})
    joined = "\n".join(strings)
    for text in expected["required_text"]:
        checks.append({"name": f"required text: {text}", "ok": text in joined})
    checks.append({"name": "no unresolved widget tokens", "ok": not bool(TOKEN_RE.search(joined))})
    actual_actions = []
    for action in actions:
        attrs = action.get("attributes", {})
        if action.get("definition") == "action/sendMessage":
            actual_actions.append({"definition": "action/sendMessage", "attribute": "content", "value": attrs.get("content")})
        elif action.get("definition") == "action/openLink":
            actual_actions.append({"definition": "action/openLink", "attribute": "url", "value": attrs.get("url")})
    for action in expected["expected_actions"]:
        checks.append({"name": f"action: {action['definition']}", "ok": action in actual_actions})
    report = {
        "representation": "widgetDefinition",
        "definitions": sorted(set(definitions)),
        "actions": actual_actions,
        "checks": checks,
        "ok": all(item["ok"] for item in checks),
    }
    base.write_json(capture_dir / "account-context.validation.json", report)
    return report


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--callback-port", type=int, default=7778)
    parser.add_argument("--callback-timeout", type=int, default=180)
    parser.add_argument("--client-id", default=None)
    parser.add_argument("--kiro-config", default="~/.kiro/settings/mcp.json")
    parser.add_argument("--token-cache", type=Path, default=base.TOKEN_CACHE_DEFAULT)
    parser.add_argument("--reauth", action="store_true", help="ignore cached refresh token and authorize in browser")
    args = parser.parse_args(argv)
    fixture = json.loads((HERE / "fixtures/account-context.json").read_text())
    try:
        template = assert_active_widget_parity("account-context")
    except WidgetTemplateError as exc:
        raise base.ProbeError(str(exc))
    if template is None:
        raise base.ProbeError("account-context: active skill has no dynamic widget")
    tokens = set(TOKEN_RE.findall(json.dumps(template)))
    values = fixture["values"]
    missing = tokens - set(values)
    if missing:
        raise base.ProbeError(f"fixture token mismatch: missing={sorted(missing)}")
    widget = hydrate(template, values)
    client_id = args.client_id or base.client_id_from_kiro_config(args.kiro_config)
    redirect_uri = f"http://localhost:{args.callback_port}/oauth/callback"
    run = HERE / "captures" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-account-context")
    run.mkdir(parents=True, exist_ok=False)
    base.write_json(run / "run-manifest.json", {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": base.MCP_URL, "protocol_version": base.PROTOCOL_VERSION,
        "redirect_uri": redirect_uri, "fixture": "active-account-context-widget-v1",
        "active_template": fixture["active_template"],
        "upstream_template": fixture["upstream_template"],
        "token_cache": str(args.token_cache),
    })
    token = base.obtain_access_token(client_id, redirect_uri, args.callback_port, args.callback_timeout, args.token_cache, args.reauth)
    mcp = base.StreamableMcp(token, run)
    mcp.call("initialize", {"protocolVersion": base.PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "salesforce-skills-account-widget-eval", "version": "0.1.0"}}, "initialize", initial=True)
    mcp.notify("notifications/initialized", {}, "initialized")
    tools = mcp.call("tools/list", {}, "tools-list")
    base.write_json(run / "tools-list.result.json", tools)
    if "display_widget" not in {tool.get("name") for tool in tools.get("tools", [])}:
        raise base.ProbeError("display_widget is not exposed by this hosted MCP connection")
    result = mcp.call("tools/call", {"name": "display_widget", "arguments": {"resourceType": "dynamic", "widgetDefinition": widget}}, "display-widget")
    base.write_json(run / "display-widget.result.json", result)
    report = validate_account_widget(result, widget, fixture["expected"], run)
    print(json.dumps({"capture_dir": str(run), "ok": report["ok"], "checks": report["checks"]}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except base.ProbeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
