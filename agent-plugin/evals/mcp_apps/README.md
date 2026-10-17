# Hosted Headless 360 MCP Apps protocol tests

This directory tests Headless 360's `display_widget` MCP Apps capability against the active
`agent-plugin/skills/` tree. The active skills preserve upstream widget-first delivery. Before
sending any widget, the contract tests prove the active renderer and variable-contract JSON
blocks match their upstream counterparts exactly; this prevents a removed or modified active
widget from producing a false pass.

The hosted tool returns a Mosaic widget definition in MCP structured metadata and advertises a
`ui://` renderer resource. A compatible host reads that `text/html;profile=mcp-app` resource
and mounts the renderer. The hosted-contract and cross-origin browser layers below verify that
flow independently of Kiro or Quick.

## Safety boundary

- Use a synthetic/demo org only. Do not run this suite against production data.
- OAuth access tokens remain in memory. After initial authorization, the refresh token is cached
  at `~/.config/salesforce-skills-evals/h360_oauth.json` with owner-only (`0600`) permissions;
  captures never contain it.
- Captured request headers and payloads are redacted before writing.
- The minimal, account-context, and batch tests submit deterministic widget fixtures only. They
  do not read or write Salesforce records, send email or Slack, navigate a browser, or execute
  widget actions.
- The cross-origin browser suite clicks every declared widget action, but its host is capture-only:
  it records and acknowledges `ui/message` and `ui/open-link` requests without sending a
  message, opening a URL, or modifying Salesforce. External hostname resolution is blocked.

## Direct hosted protocol capture

`h360_display_widget_capture.py` authenticates with OAuth PKCE, speaks Streamable HTTP MCP
directly, captures redacted raw protocol messages, and validates a minimal static-text widget.
It also follows advertised `ui://` resources and validates the returned renderer HTML when one
is supplied.

From `agent-plugin/`, after the registered ECA callback port is free (default
`http://localhost:7778/oauth/callback`):

```bash
python3 evals/mcp_apps/h360_display_widget_capture.py
```

The script reads `salesforce-h360.oauth.clientId` from `~/.kiro/settings/mcp.json` unless you
pass `--client-id` or set `H360_CLIENT_ID`. On first use (or after a revoked refresh token), it
opens browser authorization for the synthetic org. Use `--reauth` to force that path. A passing
run prints `"ok": true` and writes a timestamped directory under `captures/` containing the
redacted initialize, notification, tools-list, display response, resource response, extracted
widget JSON, validation report, and any returned HTML/DOM summary.

## Active-widget parity and contract tests

Run the offline parity gate before any hosted call:

```bash
python3 evals/mcp_apps/active_widget_contract_parity.py
```

It checks every dynamic-widget skill in the active tree and fails when an active renderer or
variable-contract JSON block is missing or differs from upstream.

### Focused account-context contract

```bash
python3 evals/mcp_apps/account_context_widget_capture.py
```

This first proves the active account-context widget blocks match upstream, then hydrates the
active renderer with `fixtures/account-context.json`. It requires the returned
`structuredContent.widgetDefinition` and `_meta["salesforce/uiMetadata"]` representations to
match the submitted active widget. It also checks expected tiles, resolved tokens, and declared
actions. It validates action descriptors; it does not execute them.

### Batch contract test

```bash
python3 evals/mcp_apps/batch_widget_contracts.py --dry-run
python3 evals/mcp_apps/batch_widget_contracts.py
```

The dry run first verifies active/upstream widget parity, then extracts and deterministically
hydrates each **active** renderer without OAuth or network calls. The hosted run sends each
hydrated active template to Headless 360 and verifies both returned widget representations,
schema-permitted tiles, non-empty text fallback, resolved tokens, and declared action payloads.
It creates a timestamped `-batch` capture directory. A successful run has an empty `failed`
list and `"ok": true`.

## Cross-origin browser and action suite (positive gate)

`cross_origin_widget_suite.py` mounts every parity-checked active widget in installed macOS
Chrome. It starts two temporary loopback servers: the host and renderer use different origins,
and the renderer iframe uses `sandbox="allow-scripts allow-same-origin"`. This preserves origin
isolation without giving the renderer the opaque origin that stalls its MCP Apps handshake.

Browser inputs come from [`fixtures/ravelin-scenario.json`](fixtures/ravelin-scenario.json) and
[`fixtures/ravelin-widget-cases.json`](fixtures/ravelin-widget-cases.json). The canonical scenario
anchors all widgets to the same Ravelin account, contacts, opportunities, portfolio, and team.
Every one of the 26 cases supplies all of its active template tokens explicitly and defines five
independent visible business assertions; generated `* fixture` values and `example.invalid` URLs
are rejected before Chrome starts.

Current verified run: 26/26 widgets, 130/130 named semantic checks, 26 screenshots, and
59/59 capture-only actions (39 `ui/message`, 20 `ui/open-link`).

Run from `agent-plugin/` with an explicitly supplied renderer HTML artifact. Captures are intentionally ignored, so do not rely on a timestamped local default:

```bash
python3 evals/mcp_apps/cross_origin_widget_suite.py --renderer-html /absolute/path/to/renderer.html
# or one widget
python3 evals/mcp_apps/cross_origin_widget_suite.py --renderer-html /absolute/path/to/renderer.html account-context
```

The standalone diagnostic shims also require the renderer path explicitly:

```bash
python3 evals/mcp_apps/renderer_mcp_apps_shim.py --renderer-html /absolute/path/to/renderer.html
python3 evals/mcp_apps/renderer_openai_shim.py --renderer-html /absolute/path/to/renderer.html
```

For every widget, the suite requires:

- the active widget blocks still match upstream;
- the renderer reaches a rendered state after exactly one tool-state delivery;
- expected hydrated text and visible geometry are present;
- the Chrome screenshot contains painted pixels below the shim header; and
- every declared button is rendered and clicked, with the resulting `ui/message` or
  `ui/open-link` request matching the active widget declaration exactly.

Actions are capture-only. The host acknowledges their MCP requests but never sends a message,
opens a URL, or writes Salesforce data. External hostname resolution is blocked in Chrome; only
the two loopback origins are reachable. Timestamped `summary.json` files and one screenshot per
skill are written under `host_captures/`, which is git-ignored.

## Official-host compatibility diagnostics

The official
[`@modelcontextprotocol/ext-apps` basic host](https://github.com/modelcontextprotocol/ext-apps/tree/main/examples/basic-host)
and MCP Inspector App Review both recognize the Headless 360 App, retrieve
`ui://widget/salesforce-widget-renderer`, and receive its populated tool result. Their current
opaque-origin sandbox path leaves this Salesforce renderer at `Loading…`, however. These hosts
are useful negative compatibility diagnostics, not the positive visual gate for this renderer.

The shim isolates the condition: an opaque sandbox sends `ui/initialize` but never completes the
handshake; the same renderer in a separate-origin sandbox with `allow-same-origin` initializes
and renders with one result delivery. Do not infer a visible pass solely from an inner-frame DOM
or successful tool response.

The repository's `reference_host_*.mjs` scripts remain diagnostic probes for the official basic
host. Their external test checkout is pinned to
[`82221c0`](https://github.com/modelcontextprotocol/ext-apps/tree/82221c0c8ce7661efa6771c9d461511b1650495f)
and lives under `/tmp/modelcontextprotocol-ext-apps`; it is not a project dependency.

## Scope and host support

Together, the parity, hosted contract, and cross-origin browser suites establish that active
widget templates match upstream, Headless 360 returns them through MCP Apps, the renderer paints
them in a compatible isolated host, and declared actions cross the host boundary safely. They do
**not** establish that every agent client uses a compatible sandbox. Quick support remains
unverified; an incompatible host must use the skill's upstream text fallback.
