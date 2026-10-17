#!/usr/bin/env python3
"""Capture and validate a raw hosted Headless 360 display_widget MCP response.

This is a protocol-level test, not a Kiro UI smoke test. It performs OAuth PKCE in a
browser, speaks Streamable HTTP MCP directly, and stores redacted raw responses under
captures/. OAuth access tokens remain in memory; after authorization, the refresh token is
cached with owner-only permissions for future test runs.

Usage:
  python3 evals/mcp_apps/h360_display_widget_capture.py
  python3 evals/mcp_apps/h360_display_widget_capture.py --callback-port 7778

The default client ID is read from ~/.kiro/settings/mcp.json -> salesforce-h360.oauth.clientId.
Use a synthetic/demo org only.
"""

import argparse
import base64
import hashlib
import html.parser
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MCP_URL = "https://api.salesforce.com/platform/mcp/v1/platform/headless-360"
AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
PROTOCOL_VERSION = "2025-06-18"
ROOT = Path(__file__).resolve().parents[2]
CAPTURES = Path(__file__).resolve().parent / "captures"
TOKEN_CACHE_DEFAULT = Path("~/.config/salesforce-skills-evals/h360_oauth.json").expanduser()
EXPECTED_TEXT = ("MCP Apps protocol probe", "Read-only display_widget contract test.")
TOKEN_RE = re.compile(r"(?i)(authorization|access_token|refresh_token|id_token|code_verifier|code|state)([\":= ]+)([^\s,}\"]+)")
UNRESOLVED_RE = re.compile(r"\{\{|\}\}|<[A-Z][A-Z0-9_]{2,}>")


class ProbeError(RuntimeError):
    pass


def redact(value):
    """Recursively redact credentials before artifacts are written."""
    if isinstance(value, str):
        return TOKEN_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: ("<redacted>" if key.lower() in {"authorization", "access_token", "refresh_token", "id_token", "code", "state", "code_verifier"} else redact(item)) for key, item in value.items()}
    return value


def write_json(path, value):
    path.write_text(json.dumps(redact(value), indent=2, ensure_ascii=False) + "\n")


def client_id_from_kiro_config(path):
    try:
        config = json.loads(Path(path).expanduser().read_text())
        return config["mcpServers"]["salesforce-h360"]["oauth"]["clientId"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ProbeError(f"could not load salesforce-h360 OAuth clientId from {path}: {exc}")


def pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def receive_oauth_callback(port, expected_state, timeout):
    received = {}
    event = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            received.update({key: values[0] for key, values in params.items() if values})
            if received.get("state") != expected_state:
                received["error"] = "OAuth callback state did not match"
            body = b"<html><body><h2>Authorization received</h2><p>You may return to the terminal.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            event.set()

        def log_message(self, *_):
            return

    server = HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        if not event.wait(timeout):
            raise ProbeError(f"OAuth callback timed out after {timeout}s")
        if "error" in received:
            raise ProbeError(f"OAuth authorization failed: {received.get('error')}: {received.get('error_description', '')}")
        if "code" not in received:
            raise ProbeError("OAuth callback contained no authorization code")
        return received["code"]
    finally:
        server.shutdown()
        server.server_close()


def token_request(values):
    body = urllib.parse.urlencode(values).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode())
    except Exception as exc:
        raise ProbeError(f"OAuth token request failed: {exc}")
    if "access_token" not in payload:
        raise ProbeError(f"OAuth token response has no access token: {redact(payload)}")
    return payload


def exchange_code(client_id, redirect_uri, code_verifier, code):
    return token_request({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "code": code,
    })


def refresh_access_token(client_id, refresh_token):
    return token_request({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    })


def load_refresh_token(path):
    try:
        return json.loads(path.read_text()).get("refresh_token")
    except (OSError, json.JSONDecodeError):
        return None


def save_refresh_token(path, refresh_token):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump({"refresh_token": refresh_token}, output)
            output.write("\n")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def obtain_access_token(client_id, redirect_uri, callback_port, callback_timeout, token_cache, force_reauth=False):
    if not force_reauth:
        refresh_token = load_refresh_token(token_cache)
        if refresh_token:
            try:
                payload = refresh_access_token(client_id, refresh_token)
                if payload.get("refresh_token"):
                    save_refresh_token(token_cache, payload["refresh_token"])
                print("Using cached Headless 360 OAuth refresh token", flush=True)
                return payload["access_token"]
            except ProbeError:
                print("Cached Headless 360 refresh token was rejected; starting browser authorization", flush=True)
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(24)
    authorize = AUTH_URL + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri,
        "scope": "mcp_api refresh_token", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    print(f"Open browser authorization for callback {redirect_uri}", flush=True)
    if not webbrowser.open(authorize):
        print("Browser did not open automatically; retry with a desktop browser available.", flush=True)
    code = receive_oauth_callback(callback_port, state, callback_timeout)
    payload = exchange_code(client_id, redirect_uri, verifier, code)
    if payload.get("refresh_token"):
        save_refresh_token(token_cache, payload["refresh_token"])
    else:
        print("OAuth response did not include a refresh token; the next run will require browser authorization.", flush=True)
    return payload["access_token"]


def parse_mcp_body(raw, content_type):
    """Return one or more JSON-RPC messages from JSON or SSE transport output."""
    text = raw.decode("utf-8", errors="replace")
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        pass
    messages = []
    for line in text.splitlines():
        if line.startswith("data:"):
            value = line[5:].strip()
            if value and value != "[DONE]":
                try:
                    messages.append(json.loads(value))
                except json.JSONDecodeError:
                    pass
    if not messages:
        raise ProbeError(f"could not parse MCP response ({content_type}): {text[:500]}")
    return messages


def advertised_ui_resource_uris(tools_result):
    """Return UI resource URIs advertised on tool metadata, including MCP Apps ui:// resources."""
    uris = []
    for tool in tools_result.get("tools", []):
        meta = tool.get("_meta", {}) if isinstance(tool, dict) else {}
        ui = meta.get("ui", {}) if isinstance(meta, dict) else {}
        uri = ui.get("resourceUri") if isinstance(ui, dict) else None
        if isinstance(uri, str):
            uris.append(uri)
    return sorted(set(uris))


class StreamableMcp:
    def __init__(self, token, capture_dir):
        self.token = token
        self.capture_dir = capture_dir
        self.session_id = None
        self.request_id = 0

    def call(self, method, params, label, initial=False):
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params}
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if not initial:
            headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
            if self.session_id:
                headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(), method="POST", headers=headers)
        status, response_headers, raw = None, {}, b""
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                status = response.status
                response_headers = dict(response.headers.items())
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            response_headers = dict(exc.headers.items())
            raw = exc.read()
        capture = {
            "request": {"method": "POST", "url": MCP_URL, "headers": headers, "jsonrpc": payload},
            "response": {"status": status, "headers": response_headers, "body": raw.decode("utf-8", errors="replace")},
        }
        write_json(self.capture_dir / f"{label}.raw.json", capture)
        if status < 200 or status >= 300:
            raise ProbeError(f"{label} returned HTTP {status}: {raw[:500].decode('utf-8', errors='replace')}")
        self.session_id = next(
            (value for key, value in response_headers.items() if key.lower() == "mcp-session-id"),
            self.session_id,
        )
        messages = parse_mcp_body(raw, response_headers.get("Content-Type", ""))
        for message in messages:
            if message.get("id") == payload["id"]:
                if "error" in message:
                    raise ProbeError(f"{label} returned JSON-RPC error: {message['error']}")
                return message["result"]
        raise ProbeError(f"{label} response did not contain request id {payload['id']}")

    def notify(self, method, params, label):
        """Send a JSON-RPC notification and capture its HTTP transport response."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(), method="POST", headers=headers)
        status, response_headers, raw = None, {}, b""
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                status = response.status
                response_headers = dict(response.headers.items())
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            response_headers = dict(exc.headers.items())
            raw = exc.read()
        write_json(self.capture_dir / f"{label}.raw.json", {
            "request": {"method": "POST", "url": MCP_URL, "headers": headers, "jsonrpc": payload},
            "response": {"status": status, "headers": response_headers, "body": raw.decode("utf-8", errors="replace")},
        })
        if status < 200 or status >= 300:
            raise ProbeError(f"{label} returned HTTP {status}: {raw[:500].decode('utf-8', errors='replace')}")


def walk(value, found):
    if isinstance(value, dict):
        if "widgetDefinition" in value and isinstance(value["widgetDefinition"], dict):
            found["widget_definitions"].append(value["widgetDefinition"])
        if isinstance(value.get("uri"), str):
            found["uris"].append(value["uri"])
        mime_type = value.get("mimeType")
        if isinstance(mime_type, str) and mime_type.lower().startswith("text/html"):
            if isinstance(value.get("text"), str):
                found["html"].append(value["text"])
            if isinstance(value.get("blob"), str):
                try:
                    found["html"].append(base64.b64decode(value["blob"]).decode("utf-8", errors="replace"))
                except Exception:
                    pass
        for child in value.values():
            walk(child, found)
    elif isinstance(value, list):
        for child in value:
            walk(child, found)
    elif isinstance(value, str) and "<!DOCTYPE html" in value.lower():
        found["html"].append(value)


class HtmlSummary(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.attrs = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


def string_values(value):
    """Collect leaf strings for token checks without mistaking JSON syntax for template braces."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for child in value for item in string_values(child)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in string_values(child)]
    return []


def validate_widget(result, capture_dir):
    found = {"widget_definitions": [], "uris": [], "html": []}
    walk(result, found)
    # Template-token checks apply to the widget data returned by display_widget, not the
    # static renderer application HTML returned from resources/read.
    response_strings = "\n".join(string_values(result.get("display_widget", result)))
    report = {
        "expected_text": list(EXPECTED_TEXT),
        "representation": [],
        "checks": [],
        "uris": sorted(set(found["uris"])),
    }
    if found["widget_definitions"]:
        report["representation"].append("widgetDefinition")
        widget = found["widget_definitions"][0]
        write_json(capture_dir / "widget-definition.extracted.json", widget)
        root = widget.get("renderer", {}).get("componentOverrides", {}).get("$", {})
        children = root.get("children", []) if isinstance(root, dict) else []
        child_text = [item.get("attributes", {}).get("text") for item in children if isinstance(item, dict)]
        report["checks"].append({"name": "widget root", "ok": root.get("definition") == "tile/widget"})
        for expected in EXPECTED_TEXT:
            report["checks"].append({"name": f"widget text: {expected}", "ok": expected in child_text})
    if found["html"]:
        report["representation"].append("html")
        for index, document in enumerate(found["html"]):
            raw_path = capture_dir / f"widget-{index}.raw.html"
            raw_path.write_text(document)
            parser = HtmlSummary()
            parser.feed(document)
            dom = {"tags": parser.tags, "text": parser.text, "attributes": parser.attrs}
            write_json(capture_dir / f"widget-{index}.dom.json", dom)
            report["checks"].append({"name": "renderer HTML has doctype", "ok": "<!doctype html" in document.lower()})
            report["checks"].append({"name": "renderer HTML has script bridge", "ok": "<script" in document.lower()})
    report["checks"].append({"name": "response strings have no unresolved tokens", "ok": not bool(UNRESOLVED_RE.search(response_strings))})
    report["checks"].append({"name": "response has at least one UI representation", "ok": bool(report["representation"] or report["uris"])})
    report["ok"] = all(check["ok"] for check in report["checks"])
    write_json(capture_dir / "validation.json", report)
    return report


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--callback-port", type=int, default=7778)
    parser.add_argument("--callback-timeout", type=int, default=180)
    parser.add_argument("--client-id", default=os.environ.get("H360_CLIENT_ID"))
    parser.add_argument("--kiro-config", default="~/.kiro/settings/mcp.json")
    parser.add_argument("--token-cache", type=Path, default=TOKEN_CACHE_DEFAULT)
    parser.add_argument("--reauth", action="store_true", help="ignore cached refresh token and authorize in browser")
    args = parser.parse_args(argv)
    client_id = args.client_id or client_id_from_kiro_config(args.kiro_config)
    redirect_uri = f"http://localhost:{args.callback_port}/oauth/callback"
    run = CAPTURES / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run.mkdir(parents=True, exist_ok=False)
    write_json(run / "run-manifest.json", {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": MCP_URL, "protocol_version": PROTOCOL_VERSION,
        "redirect_uri": redirect_uri, "fixture": "minimal-dynamic-widget-v1",
        "client_id_source": "argument/environment" if args.client_id else args.kiro_config,
        "token_cache": str(args.token_cache),
    })
    token = obtain_access_token(client_id, redirect_uri, args.callback_port, args.callback_timeout, args.token_cache, args.reauth)
    mcp = StreamableMcp(token, run)
    initialize = mcp.call("initialize", {
        "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
        "clientInfo": {"name": "salesforce-skills-mcp-apps-eval", "version": "0.1.0"},
    }, "initialize", initial=True)
    mcp.notify("notifications/initialized", {}, "initialized")
    tools = mcp.call("tools/list", {}, "tools-list")
    write_json(run / "initialize.result.json", initialize)
    write_json(run / "tools-list.result.json", tools)
    available = {tool.get("name"): tool for tool in tools.get("tools", [])}
    if "display_widget" not in available:
        raise ProbeError("display_widget is not exposed by this hosted MCP connection")
    widget = {
        "renderer": {"componentOverrides": {"$": {
            "type": "mosaic", "definition": "tile/widget", "children": [
                {"definition": "tile/text", "attributes": {"text": EXPECTED_TEXT[0], "variant": "h2"}},
                {"definition": "tile/text", "attributes": {"text": EXPECTED_TEXT[1], "variant": "body"}},
            ],
        }}}
    }
    result = mcp.call("tools/call", {
        "name": "display_widget",
        "arguments": {"resourceType": "dynamic", "widgetDefinition": widget},
    }, "display-widget")
    write_json(run / "display-widget.result.json", result)
    # Capture both UI resources advertised by the tool definition and any resources returned by the call.
    found = {"widget_definitions": [], "uris": [], "html": []}
    walk(result, found)
    resource_results = []
    advertised = advertised_ui_resource_uris(tools)
    for uri in advertised + [uri for uri in sorted(set(found["uris"])) if uri not in advertised]:
        index = len(resource_results)
        try:
            resource = mcp.call("resources/read", {"uri": uri}, f"resource-{index}")
            write_json(run / f"resource-{index}.result.json", resource)
            resource_results.append({"uri": uri, "result": resource})
        except ProbeError as exc:
            resource_results.append({"uri": uri, "error": str(exc)})
    combined = {"display_widget": result, "resources": resource_results}
    report = validate_widget(combined, run)
    report["advertised_ui_resources"] = advertised
    write_json(run / "response-extraction.json", report)
    print(json.dumps({"capture_dir": str(run), "ok": report["ok"], "representation": report["representation"], "uris": report["uris"]}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ProbeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
