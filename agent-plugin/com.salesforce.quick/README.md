# `com.salesforce.quick` host-extension namespace

This reverse-domain directory is reserved for Amazon Quick-specific material. Agent Plugins
assigns no portable meaning to it, and clients that do not implement this namespace ignore it.

## Current status

No Quick installation, Salesforce connector mapping, MCP Apps rendering, or action execution has
been verified in this repository. This directory is therefore a placeholder for future Quick
integration—not evidence that Quick supports the package or that it requires a separate UI.

The active `agent-plugin/skills/` tree retains all upstream behavior:

- all 34 upstream skills, including `using-display-widget`;
- widget-first `display_widget` instructions and complete renderer contracts;
- source text fallbacks for hosts where the tool is unavailable or cannot render; and
- only the three approved Salesforce query fixes documented in `skills/README.md`.

Protocol and renderer behavior are documented in
[`../evals/mcp_apps/README.md`](../evals/mcp_apps/README.md). Headless 360 accepts all 26 active
widgets, and they render in a compatible separate-origin sandbox. The official basic host and
MCP Inspector currently stall with the Salesforce renderer on their opaque-origin path. Quick's
sandbox behavior is unknown.

## `ui/`

`ui/` records possible future Quick-specific adaptation guidance. Do not use it to replace or
remove the active MCP Apps widget definitions unless Quick testing demonstrates that a separate
surface is necessary and the change is explicitly approved.

Any future Quick action must preserve the source skill's consent posture. Read-only views stay
read-only; draft actions remain drafts until a person approves the exact content and destination.
