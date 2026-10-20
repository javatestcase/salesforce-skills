# `com.salesforce.quick` host-extension namespace

This reverse-domain directory is reserved for Amazon Quick-specific material. Agent Plugins
assigns no portable meaning to it, and clients that do not implement this namespace ignore it.

## Current status

Synthetic Quick runs validated `calendar-events` and `customer-health` through Headless 360 reads and rendered widgets. After the pre-dispatch safeguard was added, a fresh health run completed without the earlier rewritten-query syntax error. A later run confirmed the health case-total correction. A `customer-voice` rerun followed the local source and zero-quote rules. `daily-briefing` reruns showed the meeting-account correction, verbatim row names, and the inbox check. `deal-advance-gap` reruns showed its lookup, stage-order, row-state, and suggested-step changes. Other skills, connector mapping, and action execution remain unverified in this repository.

The active `agent-plugin/skills/` tree retains all upstream behavior:

- all 34 upstream skills, including `using-display-widget`;
- widget-first `display_widget` instructions and complete renderer contracts;
- source text fallbacks for hosts where the tool is unavailable or cannot render; and
- the twelve approved deviations documented in [`CONVERSION_RECIPE.md`](../CONVERSION_RECIPE.md), including the local account-context, account-tiering, calendar, customer-health, customer-voice, daily-briefing, deal-advance-gap, deal-review, and deal-signals adaptations.

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
