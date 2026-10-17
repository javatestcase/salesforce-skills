# Upstream Sync and Deviation Policy

`agent-plugin/skills/` is not a rewritten Markdown-first fork. It is an active mirror of
`salesforce-for-sales/skills/` packaged under the Agent Plugins standard.

## Mirror invariant

- **Source:** `salesforce-for-sales/skills/<name>/SKILL.md`
- **Active mirror:** `agent-plugin/skills/<name>/SKILL.md`
- Mirror every upstream skill directory and file.
- Preserve complete file content: frontmatter, global rules, Headless 360 calls,
  `display_widget` instructions, variable contracts, renderer JSON, action definitions, text
  fallbacks, and error recovery.
- Do not make host-neutral wording changes, promote the fallback, add queries, or redesign UI
  while synchronizing upstream.
- Keep evaluation files under `agent-plugin/evals/`; nothing eval-only belongs in a shipped
  skill directory.

## Allowed deviations

Only fixes backed by the three filed upstream issues may differ:

| Skill | Issue | Patch |
|---|---|---|
| `lead-triage` | [#9](https://github.com/salesforce/salesforce-skills/issues/9) | Add `... on Group { Name { value } }` beside the User fragment for `Lead.Owner`. |
| `forecast-narrative` | [#15](https://github.com/salesforce/salesforce-skills/issues/15) | Change only the field-history predicate to `CreatedDate >= %QSTART%T00:00:00Z`. |
| `weekly-wrap` | [#16](https://github.com/salesforce/salesforce-skills/issues/16) | Keep all six detail and six aggregate roots, but send them as two parallel `dispatch_readonly` calls and update the directly affected fallback wording. |

Do not preserve unrelated local product changes during a refresh. A fourth deviation requires a
separate review and an explicit update to this allowlist.

## Synchronizing a new upstream version

1. Replace the active skill tree from the new upstream tree verbatim.
2. Confirm source and active skill inventories match exactly.
3. Reapply only the three patches above.
4. Generate `docs/portable-skill-diff-report.md`; it must show 31 exact matches and only the
   three allowed differences.
5. Run the validation sequence below before review.

Copy nested query strings rather than retyping them. The JSON-inside-JSON escaping is easy to
corrupt, and `validate.py` deliberately decodes every `queryInput` and checks bracket nesting.

## Delivery behavior

Preserve upstream output semantics:

- When `display_widget` is available and the host can mount the Salesforce MCP App, the widget
  is the primary output.
- If the tool is unavailable, errors, or the host cannot render it, use the source text fallback.
- Keep `using-display-widget`; it documents the renderer contract used by the other skills.
- Do not disable or remove widget content as a portability transformation.

Host compatibility is separate from skill fidelity. The current Salesforce renderer works in a
separate-origin sandbox with `allow-same-origin`, but stalls in the opaque-origin path used by
the official basic host and MCP Inspector. Quick rendering remains unverified. See
[`evals/mcp_apps/README.md`](evals/mcp_apps/README.md).

## Validation

Run from `agent-plugin/`:

```bash
# Static packaging/frontmatter/query checks
python3 evals/validate.py

# Exact upstream widget-block parity
python3 evals/mcp_apps/active_widget_contract_parity.py

# Offline and hosted widget contracts
python3 evals/mcp_apps/batch_widget_contracts.py --dry-run
python3 evals/mcp_apps/batch_widget_contracts.py

# Meaningful browser rendering and capture-only actions
python3 evals/mcp_apps/cross_origin_widget_suite.py

# Synthetic-org reads
python3 evals/run_reads.py --org <sandbox-alias>
python3 evals/e2e_calls.py --org <sandbox-alias>
```

Use only a synthetic or sandbox org. The local MCP adapter used by `e2e_calls.py` accepts only
GET GraphQL/SOQL reads and rejects POST, non-query endpoints, GraphQL mutations, and non-SELECT
SOQL before contacting Salesforce.

## Current verified baseline

- 34 active skills; 31 byte-identical to upstream and three approved fixes.
- Static validator: PASS.
- Live read fixtures on `genwatt-demo`: PASS.
- Exact skill calls on `genwatt-demo`: 155/155, with all four read-only guards passing.
- Active widget parity and hosted widget contracts: 26/26.
- Ravelin browser suite: 26/26 widgets, 130/130 semantic checks, and 59/59 captured
  actions (39 messages and 20 links), with no external effect.
