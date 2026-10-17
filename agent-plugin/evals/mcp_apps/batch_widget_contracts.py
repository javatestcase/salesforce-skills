#!/usr/bin/env python3
"""Validate active dynamic-widget contracts through hosted Headless 360.

For every active skill, this runner first proves its upstream dynamic widget blocks match
byte-for-byte, then hydrates the active renderer definition and submits it to Headless 360.
It validates structuredContent, Salesforce UI metadata, tile/action definitions, fully resolved
tokens, and text fallback. No Salesforce record read/write, email, Slack, browser navigation, or
widget action execution is performed; widget inputs are deterministic test values.
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
PLUGIN_ROOT = HERE.parents[1]
REPO_ROOT = PLUGIN_ROOT.parent
SOURCE_SKILLS = REPO_ROOT / "salesforce-for-sales/skills"
ACTIVE_SKILLS = PLUGIN_ROOT / "skills"
SCHEMA_PATH = SOURCE_SKILLS / "using-display-widget/widget-definition.schema.json"
TOKEN_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


def inferred_values(template):
    """Generate valid deterministic values from the renderer's typed tile positions."""
    values = {}
    array_attrs = {"children", "categories", "series", "slices", "bands", "rows", "columns", "steps", "cells", "days", "data", "domain", "xLabels", "yLabels"}
    number_attrs = {"value", "target", "max", "min", "totalRows", "baseline"}
    object_attrs = {"start", "end"}

    def add(token, attr, definition):
        if token in values:
            return
        if definition == "action/openLink" or attr == "url":
            values[token] = "https://example.invalid/mcp-apps-probe"
        elif definition == "action/sendMessage" or attr == "content":
            values[token] = "MCP Apps action contract probe"
        elif attr in object_attrs:
            values[token] = {"label": f"{token} fixture", "value": 1}
        elif attr in array_attrs:
            if attr == "categories":
                values[token] = ["Fixture A"]
            elif attr == "series":
                values[token] = [{"name": "Fixture", "data": [1]}]
            elif attr == "slices":
                values[token] = [{"label": "Fixture", "value": 1}]
            elif attr == "bands":
                values[token] = [{"from": 0, "to": 1, "variant": "info", "label": "Fixture"}]
            elif attr == "steps":
                values[token] = [{"label": "Fixture", "delta": 1}]
            elif attr == "domain":
                values[token] = [0, 1]
            elif attr in {"xLabels", "yLabels"}:
                values[token] = ["Fixture A"]
            elif attr == "cells":
                values[token] = [{"x": 0, "y": 0, "value": 1, "valueLabel": "Fixture"}]
            elif attr == "data":
                values[token] = [1]
            else:
                values[token] = []
        elif attr in number_attrs and definition in {"tile/meter", "tile/datagrid", "tile/sparkline", "tile/heatmap"}:
            values[token] = 1
        else:
            values[token] = f"{token} fixture"

    def visit(value, attr=None, definition=None):
        if isinstance(value, str):
            exact = TOKEN_RE.fullmatch(value)
            if exact:
                add(exact.group(1), attr, definition)
            else:
                for token in TOKEN_RE.findall(value):
                    add(token, attr, definition)
        elif isinstance(value, list):
            for child in value:
                visit(child, attr, definition)
        elif isinstance(value, dict):
            local_definition = value.get("definition", definition)
            if isinstance(value.get("attributes"), dict):
                for key, child in value["attributes"].items():
                    visit(child, key, local_definition)
            for key, child in value.items():
                if key != "attributes":
                    visit(child, key, local_definition)

    visit(template)
    return values


def hydrate(value, values):
    if isinstance(value, str):
        exact = TOKEN_RE.fullmatch(value)
        if exact:
            return values[exact.group(1)]
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
        for child in value.values():
            walk(child, definitions, actions, strings)
    elif isinstance(value, list):
        for child in value:
            walk(child, definitions, actions, strings)
    elif isinstance(value, str):
        strings.append(value)


def validate(skill, result, widget, allowed_tiles, capture_dir):
    structured = result.get("structuredContent", {}).get("widgetDefinition")
    metadata = result.get("_meta", {}).get("salesforce/uiMetadata")
    definitions, actions, strings = [], [], []
    walk(widget, definitions, actions, strings)
    allowed_definitions = allowed_tiles | {"tile/widget", "tile/mosaic"}
    checks = [
        {"name": "structuredContent widgetDefinition", "ok": structured == widget},
        {"name": "salesforce/uiMetadata", "ok": metadata == widget},
        {"name": "tile/widget root", "ok": widget.get("renderer", {}).get("componentOverrides", {}).get("$", {}).get("definition") == "tile/widget"},
        {"name": "all tile definitions allowed by schema", "ok": all(item in allowed_definitions or item.startswith("action/") for item in definitions)},
        {"name": "no unresolved widget tokens", "ok": not bool(TOKEN_RE.search("\n".join(strings)))},
        {"name": "non-empty text fallback", "ok": bool(result.get("content", [{}])[0].get("text", "").strip())},
    ]
    action_rows = []
    for action in actions:
        attrs = action.get("attributes", {})
        action_rows.append({"definition": action["definition"], "attributes": attrs})
        if action["definition"] == "action/sendMessage":
            checks.append({"name": "sendMessage content", "ok": isinstance(attrs.get("content"), str) and bool(attrs["content"].strip())})
        if action["definition"] == "action/openLink":
            checks.append({"name": "openLink URL", "ok": isinstance(attrs.get("url"), str) and attrs["url"].startswith(("https://", "http://"))})
    report = {"skill": skill, "definitions": sorted(set(definitions)), "actions": action_rows, "checks": checks, "ok": all(check["ok"] for check in checks)}
    base.write_json(capture_dir / f"{skill}.validation.json", report)
    return report


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--callback-port", type=int, default=7778)
    parser.add_argument("--callback-timeout", type=int, default=180)
    parser.add_argument("--client-id", default=None)
    parser.add_argument("--kiro-config", default="~/.kiro/settings/mcp.json")
    parser.add_argument("--token-cache", type=Path, default=base.TOKEN_CACHE_DEFAULT)
    parser.add_argument("--reauth", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="extract/hydrate/validate locally; do not call Headless 360")
    parser.add_argument("skills", nargs="*", help="optional active skill names")
    args = parser.parse_args(argv)

    schema = json.loads(SCHEMA_PATH.read_text())
    allowed_tiles = set(schema["$defs"]["block"]["properties"]["definition"]["enum"])
    selected = args.skills or sorted(path.name for path in ACTIVE_SKILLS.iterdir() if (path / "SKILL.md").is_file())
    fixtures, skipped = {}, []
    for skill in selected:
        source = SOURCE_SKILLS / skill / "SKILL.md"
        active = ACTIVE_SKILLS / skill / "SKILL.md"
        if not source.is_file():
            raise base.ProbeError(f"{skill}: no upstream source")
        if not active.is_file():
            raise base.ProbeError(f"{skill}: no active skill")
        try:
            template = assert_active_widget_parity(skill)
        except WidgetTemplateError as exc:
            raise base.ProbeError(str(exc))
        if template is None:
            skipped.append(skill)
            continue
        values = inferred_values(template)
        tokens = set(TOKEN_RE.findall(json.dumps(template)))
        missing = tokens - set(values)
        if missing:
            raise base.ProbeError(f"{skill}: inference missing values for {sorted(missing)}")
        fixtures[skill] = hydrate(template, values)

    if args.dry_run:
        reports = []
        for skill, widget in fixtures.items():
            definitions, actions, strings = [], [], []
            walk(widget, definitions, actions, strings)
            reports.append({"skill": skill, "tokens": len(TOKEN_RE.findall(json.dumps(widget))), "definitions": sorted(set(definitions)), "actions": len(actions), "ok": not bool(TOKEN_RE.search("\n".join(strings)))})
        print(json.dumps({"tested": reports, "skipped": skipped}, indent=2))
        return 0 if all(item["ok"] for item in reports) else 1

    client_id = args.client_id or base.client_id_from_kiro_config(args.kiro_config)
    redirect_uri = f"http://localhost:{args.callback_port}/oauth/callback"
    run = HERE / "captures" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-batch")
    run.mkdir(parents=True, exist_ok=False)
    base.write_json(run / "run-manifest.json", {"captured_at_utc": datetime.now(timezone.utc).isoformat(), "endpoint": base.MCP_URL, "fixture": "active-widget-contract-batch-v1", "skills": sorted(fixtures), "skipped": skipped, "redirect_uri": redirect_uri, "token_cache": str(args.token_cache)})
    token = base.obtain_access_token(client_id, redirect_uri, args.callback_port, args.callback_timeout, args.token_cache, args.reauth)
    mcp = base.StreamableMcp(token, run)
    mcp.call("initialize", {"protocolVersion": base.PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "salesforce-skills-widget-batch-eval", "version": "0.1.0"}}, "initialize", initial=True)
    mcp.notify("notifications/initialized", {}, "initialized")
    tools = mcp.call("tools/list", {}, "tools-list")
    base.write_json(run / "tools-list.result.json", tools)
    if "display_widget" not in {tool.get("name") for tool in tools.get("tools", [])}:
        raise base.ProbeError("display_widget is not exposed by this hosted MCP connection")
    reports = []
    for skill, widget in fixtures.items():
        result = mcp.call("tools/call", {"name": "display_widget", "arguments": {"resourceType": "dynamic", "widgetDefinition": widget}}, f"{skill}.display-widget")
        base.write_json(run / f"{skill}.display-widget.result.json", result)
        reports.append(validate(skill, result, widget, allowed_tiles, run))
    summary = {"tested": len(reports), "skipped": skipped, "passed": [report["skill"] for report in reports if report["ok"]], "failed": [report["skill"] for report in reports if not report["ok"]]}
    summary["ok"] = not summary["failed"]
    base.write_json(run / "batch-summary.json", summary)
    print(json.dumps({"capture_dir": str(run), **summary}, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except base.ProbeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
