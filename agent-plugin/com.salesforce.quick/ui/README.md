# Quick UI integration placeholder

The active skills already contain their upstream Headless 360 MCP Apps widgets and the shared
`using-display-widget` guidance. This directory does not replace those contracts.

Amazon Quick rendering has not been tested. If Quick mounts the Headless 360 MCP App in a
compatible sandbox, it can use the existing widget definitions directly. If it does not, this
folder may later contain a Quick-native adaptation that consumes the same assembled data while
preserving the source text fallback.

Current renderer evidence:

- 26/26 active widget blocks match upstream.
- 26/26 live Headless 360 widget responses preserve the submitted structured data and metadata.
- 26/26 meaningful Ravelin widgets render in a separate-origin sandbox with
  `allow-same-origin`.
- 130/130 semantic checks and 59/59 capture-only actions pass.
- The official basic host and MCP Inspector opaque-origin paths stall at `Loading…` for this
  Salesforce renderer.

See [`../../evals/mcp_apps/README.md`](../../evals/mcp_apps/README.md). Any future Quick-native
button must preserve the original skill's safety contract: read-only actions remain read-only,
and draft/send workflows must never send without explicit human approval.
