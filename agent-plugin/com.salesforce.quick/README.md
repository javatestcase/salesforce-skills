# `com.salesforce.quick` — host extension namespace

This directory is the plugin's **reverse-domain client extension** under the Agent Plugins
standard. Per the spec, Agent Plugins assigns no portable meaning to its contents — it holds
**host-specific** material that is deliberately *not* part of the portable core (`plugin.json`
+ `skills/`). Clients that don't implement this namespace ignore it.

Here it carries the **Amazon Quick** rich-UI layer. The portable skills each end with a
"Rich visualization (host-specific — optional)" section that points here; when a skill runs
on Quick, the host can render a visual layout **in addition to** the skill's portable
Markdown output. When no rich surface is available, the Markdown is the whole deliverable —
nothing here is required for a skill to work.

## `ui/`

Rendering guidance and templates for Quick's UI surfaces (Quick Sight dashboards / Apps in
Quick). This is where the retired `using-display-widget` guidance lives: it was a Claude/
Cowork renderer reference (the `display_widget` MCP-Apps capability), which is **not portable**
and does not belong in `skills/`. It is kept here as host guidance for building the Quick
equivalent.

> Note: `display_widget` and the Claude widget JSON templates are Claude-specific. On Quick,
> the visual layer is built with Quick's own surfaces, not `display_widget`. The mapping from
> the old widget layouts to Quick UI is a Phase-3 task in
> [`../../QUICK_MIGRATION_PLAN.md`](../../QUICK_MIGRATION_PLAN.md); this directory is the
> place for it.

## Safety carries over

Any interactive element rendered here inherits the skill's consent posture: read-only skills
render read-only views; draft/send skills' action buttons must **draft or propose, never send
or write** without explicit human approval. See each skill's `evals/skills/<name>/eval.yaml`
(`safety` / `email_eval`).
