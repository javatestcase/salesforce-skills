#!/usr/bin/env python3
"""Offline policy tests for the restricted Headless 360 diagnostic bridge."""

import http.client
import importlib.util
import json
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("h360_mcp_bridge", HERE / "h360_mcp_bridge.py")
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


class Provider:
    def __init__(self):
        self.calls = 0
        self.invalidations = 0

    def get(self):
        self.calls += 1
        return "test-token"

    def invalidate(self):
        self.invalidations += 1


class Response:
    def __init__(self, body, headers=None):
        self.status = 200
        self.headers = headers or {"Content-Type": "application/json"}
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Upstream:
    RESOURCE = "ui://widget/salesforce-widget-renderer"

    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        message = json.loads((request.data or b"{}").decode())
        self.calls.append(message)
        method = message.get("method")
        if method == "tools/list":
            result = {"tools": [{"name": "display_widget", "_meta": {"ui": {"resourceUri": self.RESOURCE}}}]}
        else:
            result = {}
        body = json.dumps({"jsonrpc": "2.0", "id": message.get("id"), "result": result}).encode()
        return Response(body, {"Content-Type": "application/json", "Mcp-Session-Id": "session-1"})


class BridgeTestCase(unittest.TestCase):
    def setUp(self):
        self.provider = Provider()
        self.state = bridge.BridgeState()
        self.upstream = Upstream()
        self.server = bridge.ThreadingHTTPServer(("127.0.0.1", 0), bridge.make_handler(self.provider, self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.urlopen = mock.patch.object(bridge.urllib.request, "urlopen", side_effect=self.upstream)
        self.urlopen.start()

    def tearDown(self):
        self.urlopen.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, payload=None, session=None):
        headers = {}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload)
        if session:
            headers["Mcp-Session-Id"] = session
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, "/mcp", body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        return response.status, json.loads(raw) if raw else {}

    def initialize(self):
        status, _ = self.request("POST", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(200, status)
        self.assertEqual("session-1", self.state.session_id)

    def test_allows_only_the_display_widget_evaluation_sequence(self):
        self.initialize()
        session = self.state.session_id
        sequence = [
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "display_widget", "arguments": {"resourceType": "dynamic", "widgetDefinition": {}}}},
            {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": Upstream.RESOURCE}},
        ]
        for message in sequence:
            status, _ = self.request("POST", message, session)
            self.assertEqual(200, status)
        self.assertEqual({Upstream.RESOURCE}, self.state.allowed_resources)
        self.assertEqual(5, self.provider.calls)
        self.assertEqual(5, len(self.upstream.calls))

    def test_rejected_requests_never_obtain_a_token_or_reach_upstream(self):
        rejected = [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "dispatch", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": "file:///tmp/not-allowed"}},
            [{"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}],
        ]
        for message in rejected:
            status, _ = self.request("POST", message)
            self.assertIn(status, {400, 403})
        status, _ = self.request("GET")
        self.assertEqual(403, status)
        self.assertEqual(0, self.provider.calls)
        self.assertEqual([], self.upstream.calls)

    def test_display_widget_requires_dynamic_native_widget_definition(self):
        self.initialize()
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "display_widget", "arguments": {"resourceType": "salesforce_widget"}}}
        status, _ = self.request("POST", message, self.state.session_id)
        self.assertEqual(403, status)
        self.assertEqual(1, self.provider.calls)
        self.assertEqual(1, len(self.upstream.calls))


if __name__ == "__main__":
    unittest.main()
