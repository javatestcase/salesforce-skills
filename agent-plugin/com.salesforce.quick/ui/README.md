# Quick UI layer (host-specific)

Rendering guidance for the optional rich-visualization layer on Amazon Quick. Populated in
Phase 3 of the migration plan. Not part of the portable skill core.

## Origin: the retired `using-display-widget` skill

In the original Claude/Cowork plugin, a shared skill called `using-display-widget` taught the
agent to render results with the `display_widget` MCP-Apps tool (a hydrated renderer
definition, or a pre-registered widget with props). That capability is **Claude-specific** and
was intentionally **not** ported into `skills/` — it isn't portable, and each skill's rich
view is host-dependent.

## What replaces it on Quick

- **`display_widget` → Quick surfaces.** Quick renders visuals through Quick Sight dashboards
  and Apps in Quick, not inline widget JSON. The per-skill widget layouts from the Claude
  plugin (datagrids, callouts, KPI strips, sparklines) map onto Quick components.
- **Data contract stays the same.** The skills already assemble the underlying data (rows,
  amounts, stages, flags) for their portable Markdown output; the Quick UI consumes that same
  assembled data.
- **Actions.** Where the Claude widgets used `action/sendMessage` buttons, Quick uses its own
  action model. The safety rule is unchanged: buttons on read-only skills stay read-only;
  buttons on draft/send skills must draft/propose, never send or write, without explicit
  approval.

## Per-skill layouts to build (Phase 3)

The skills whose Claude versions shipped a widget (candidates for a Quick visual): `daily-briefing`,
`call-prep`, `draft-outreach`, `lead-triage`, `inbox-sweep`, `weekly-wrap`,
`salesforce-hygiene-check`, plus any dashboard-style read skills (`pipeline-review`,
`team-pipeline`, `forecast-narrative`, etc.). Each remains fully functional without this
layer — the portable Markdown is the guaranteed output.
