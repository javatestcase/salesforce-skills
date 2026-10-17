#!/usr/bin/env python3
"""Restricted local bridge for the official MCP Apps basic-host diagnostic.

The bridge is intentionally limited to the hosted ``display_widget`` evaluation flow. It
never forwards arbitrary Headless 360 tools, and rejects invalid requests before obtaining
an OAuth token. It is diagnostic-only and is not a general MCP proxy.
"""

import argparse
import importlib.util
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "h360_display_widget_capture.py"
spec = importlib.util.spec_from_file_location("h360_capture", BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

FORWARD_REQUEST_HEADERS = {"accept", "content-type", "mcp-session-id", "mcp-protocol-version", "last-event-id"}
FORWARD_RESPONSE_HEADERS = {"content-type", "mcp-session-id", "mcp-protocol-version", "cache-control"}
MAX_REQUEST_BYTES = 1_000_000


class PolicyError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class BridgeState:
    def __init__(self):
        self.session_id = None
        self.allowed_resources = set()


def response_header(headers, name):
    """Return a case-insensitive response header value."""
    return next((value for key, value in headers.items() if key.lower() == name.lower()), None)


def require_object(value, label):
    if not isinstance(value, dict):
        raise PolicyError(400, f"{label} must be an object")
    return value


def validate_jsonrpc(message, state):
    """Reject any request outside the evaluator's documented protocol sequence."""
    require_object(message, "JSON-RPC message")
    if message.get("jsonrpc") != "2.0":
        raise PolicyError(400, "jsonrpc must be '2.0'")
    method = message.get("method")
    if not isinstance(method, str):
        raise PolicyError(400, "method must be a string")
    params = message.get("params", {})
    require_object(params, "params")
    has_id = "id" in message

    if method == "initialize":
        if not has_id:
            raise PolicyError(400, "initialize must be a request")
        return
    if method == "notifications/initialized":
        if has_id:
            raise PolicyError(400, "notifications/initialized must be a notification")
        return
    if method == "tools/list":
        if not has_id:
            raise PolicyError(400, "tools/list must be a request")
        return
    if method == "tools/call":
        if not has_id:
            raise PolicyError(400, "tools/call must be a request")
        if params.get("name") != "display_widget":
            raise PolicyError(403, "only display_widget is permitted")
        arguments = require_object(params.get("arguments"), "display_widget arguments")
        if arguments.get("resourceType") != "dynamic":
            raise PolicyError(403, "only dynamic display_widget resources are permitted")
        require_object(arguments.get("widgetDefinition"), "widgetDefinition")
        return
    if method == "resources/read":
        if not has_id:
            raise PolicyError(400, "resources/read must be a request")
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri.startswith("ui://") or uri not in state.allowed_resources:
            raise PolicyError(403, "resource is not advertised by display_widget")
        return
    raise PolicyError(403, f"method is not permitted: {method}")


def parse_request(body, state):
    if not body:
        raise PolicyError(400, "POST body is required")
    try:
        message = json.loads(body)
    except json.JSONDecodeError as exc:
        raise PolicyError(400, f"invalid JSON: {exc.msg}") from exc
    if isinstance(message, list):
        raise PolicyError(400, "JSON-RPC batches are not permitted")
    validate_jsonrpc(message, state)
    return message


def cache_upstream_state(message, response_headers, payload, state):
    session_id = response_header(response_headers, "mcp-session-id")
    if session_id:
        state.session_id = session_id
    if message.get("method") != "tools/list":
        return
    try:
        responses = base.parse_mcp_body(payload, response_header(response_headers, "content-type") or "")
    except base.ProbeError:
        return
    for response in responses:
        if response.get("id") != message.get("id") or not isinstance(response.get("result"), dict):
            continue
        state.allowed_resources.update(
            uri for uri in base.advertised_ui_resource_uris(response["result"])
            if uri.startswith("ui://")
        )


class TokenProvider:
    def __init__(self, client_id, token_cache):
        self.client_id = client_id
        self.token_cache = token_cache
        self.token = None

    def get(self):
        if not self.token:
            self.token = base.obtain_access_token(
                self.client_id,
                "http://localhost:7778/oauth/callback",
                7778,
                180,
                self.token_cache,
            )
        return self.token

    def invalidate(self):
        self.token = None


def make_handler(provider, state=None):
    state = state or BridgeState()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print("[h360-bridge] " + fmt % args, flush=True)

        def cors(self):
            self.send_header("Access-Control-Allow-Origin", "http://localhost:8080")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type, Mcp-Session-Id, MCP-Protocol-Version, Last-Event-ID")
            self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id, MCP-Protocol-Version")

        def reject(self, status, message):
            payload = json.dumps({"error": message}).encode()
            self.send_response(status)
            self.cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def bound_session(self):
            return bool(state.session_id and self.headers.get("Mcp-Session-Id") == state.session_id)

        def forward_upstream(self, body, message=None):
            headers = {
                key: value for key, value in self.headers.items()
                if key.lower() in FORWARD_REQUEST_HEADERS
            }
            headers["Authorization"] = f"Bearer {provider.get()}"
            request = urllib.request.Request(base.MCP_URL, data=body, method=self.command, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    status = response.status
                    response_headers = dict(response.headers.items())
                    payload = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                response_headers = dict(exc.headers.items())
                payload = exc.read()
                if status == 401:
                    provider.invalidate()
            except urllib.error.URLError as exc:
                self.reject(502, f"upstream MCP request failed: {exc.reason}")
                return

            if message is not None and 200 <= status < 300:
                cache_upstream_state(message, response_headers, payload, state)
            self.send_response(status)
            for key, value in response_headers.items():
                if key.lower() in FORWARD_RESPONSE_HEADERS:
                    self.send_header(key, value)
            self.cors()
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_OPTIONS(self):
            self.send_response(204)
            self.cors()
            self.end_headers()

        def do_GET(self):
            if self.path.split("?", 1)[0] != "/mcp":
                self.reject(404, "only /mcp is available")
                return
            if not self.bound_session():
                self.reject(403, "a bound MCP session is required")
                return
            self.forward_upstream(None)

        def do_POST(self):
            if self.path.split("?", 1)[0] != "/mcp":
                self.reject(404, "only /mcp is available")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.reject(400, "Content-Length must be an integer")
                return
            if length < 1 or length > MAX_REQUEST_BYTES:
                self.reject(413, "request body is missing or too large")
                return
            body = self.rfile.read(length)
            try:
                message = parse_request(body, state)
            except PolicyError as exc:
                self.reject(exc.status, str(exc))
                return
            if message["method"] != "initialize" and not self.bound_session():
                self.reject(403, "a bound MCP session is required")
                return
            self.forward_upstream(body, message)

    return Handler


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--client-id", default=None)
    parser.add_argument("--kiro-config", default="~/.kiro/settings/mcp.json")
    parser.add_argument("--token-cache", type=Path, default=base.TOKEN_CACHE_DEFAULT)
    args = parser.parse_args(argv)
    client_id = args.client_id or base.client_id_from_kiro_config(args.kiro_config)
    provider = TokenProvider(client_id, args.token_cache)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(provider))
    print(f"[h360-bridge] serving restricted display_widget bridge at http://localhost:{args.port}/mcp", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        pass
