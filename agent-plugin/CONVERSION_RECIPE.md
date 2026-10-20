# Upstream Sync and Deviation Policy

`agent-plugin/skills/` is not a rewritten Markdown-first fork. It is an active mirror of
`salesforce-for-sales/skills/` packaged under the Agent Plugins standard.

## Mirror invariant

- **Source:** `salesforce-for-sales/skills/<name>/SKILL.md`
- **Active mirror:** `agent-plugin/skills/<name>/SKILL.md`
- Mirror every upstream skill directory and file.
- Preserve complete file content: frontmatter, global rules, Headless 360 calls,
  `display_widget` instructions, variable contracts, renderer JSON, action definitions, text
  fallbacks, and error recovery, unless an allowlisted deviation below explicitly says otherwise.
- Do not make host-neutral wording changes, promote the fallback, add queries, or redesign UI
  while synchronizing upstream.
- Keep evaluation files under `agent-plugin/evals/`; nothing eval-only belongs in a shipped
  skill directory.

## Allowed deviations

Approved deviations are limited to the twelve skill entries below. Five correct filed upstream
defects, including `deal-advance-gap`
([#23](https://github.com/salesforce/salesforce-skills/issues/23) and [#24](https://github.com/salesforce/salesforce-skills/issues/24)); `account-context`, `account-tiering`, `customer-health`, `customer-voice`, and
`daily-briefing` are Quick/Kiro adaptations backed by synthetic host traces. `customer-health` also carries a case-total correction filed upstream as
[#21](https://github.com/salesforce/salesforce-skills/issues/21). `daily-briefing` also carries a meeting-account
correction filed upstream as [#22](https://github.com/salesforce/salesforce-skills/issues/22). `deal-advance-gap` also carries
Quick/Kiro row-state and suggested-step rules alongside its two filed corrections. `deal-signals` carries a widget
output correction filed upstream as [#25](https://github.com/salesforce/salesforce-skills/issues/25), plus Quick/Kiro stale-commitment,
email-evidence, and complete-digest rules. `deal-review` carries a multiple-match correction filed
upstream as [#26](https://github.com/salesforce/salesforce-skills/issues/26), and the
[#24](https://github.com/salesforce/salesforce-skills/issues/24) stage-order read for its stage tile, noted in a [follow-up comment](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032) on #24.

| Skill | Evidence | Patch |
|---|---|---|
| `account-context` | Synthetic Quick trace | Preserve the canonical deep query, substitute only documented placeholders, and rebuild once from the standard-field literal after a syntax failure. |
| `account-tiering` | Synthetic Quick traces | Reconcile the heatmap with the binary tier threshold and omit unavailable ARR/Whitespace metrics rather than defaulting them to zero. |
| `lead-triage` | [#9](https://github.com/salesforce/salesforce-skills/issues/9) | Add `... on Group { Name { value } }` beside the User fragment for `Lead.Owner`. |
| `forecast-narrative` | [#15](https://github.com/salesforce/salesforce-skills/issues/15) | Change only the field-history predicate to `CreatedDate >= %QSTART%T00:00:00Z`. |
| `weekly-wrap` | [#16](https://github.com/salesforce/salesforce-skills/issues/16) | Keep all six detail and six aggregate roots, but send them as two parallel `dispatch_readonly` calls and update the directly affected fallback wording. |
| `calendar-events` | [#20](https://github.com/salesforce/salesforce-skills/issues/20) | Add typed, grounded `What` data for deal output and remove the unsupported attendee count from the active subtitle; keep the renderer JSON identical to upstream. |
| `customer-health` | Synthetic Quick trace; [#21](https://github.com/salesforce/salesforce-skills/issues/21) | Preserve and preflight the canonical deep Account `queryInput` before the first dispatch; on syntax failure, rebuild once from the literal standard-field template. Add aggregate case totals to the same request and take every Support count from them. Show `account-context`'s object-not-string `widgetDefinition` example at the widget call. |
| `customer-voice` | Synthetic Quick trace | Take quotes only from the docs and email searches, with no Salesforce reads beyond the three scoping reads and no counts from other records. With no quote, keep the output template with 0 quotes, the topic, the period, and gaps, and offer at most one in-skill next step. |
| `daily-briefing` | Synthetic Quick trace; [#22](https://github.com/salesforce/salesforce-skills/issues/22) | Copy closing-soon and past-due row names from the returned values: use the Opportunity Name unchanged when it already begins with the Account Name, otherwise `<Account> — <Opp Name>`; never retype, shorten, or reword a name. Select Event `AccountId` in the calendar read and pass those Ids to the meeting-account read, keeping the domain match as the fallback. When an email tool is available, run the inbox and "you owe them" checks and report the result in the follow-ups stat and inbox block; otherwise say the inbox was not checked instead of dropping it. |
| `deal-advance-gap` | Synthetic Quick traces; [#23](https://github.com/salesforce/salesforce-skills/issues/23); [#24](https://github.com/salesforce/salesforce-skills/issues/24) | In the step 2a name lookup, search open deals only (`IsClosed: { eq: false }`) and select `totalCount`; when the total exceeds the rows returned, narrow the search once instead of offering a cut-off list, and include the account name when the request gives one. Add an aliased `stages` root to the step 1 read that returns the Stage picklist in the org's order (master record type), and take the default target from it. Rest every Done, In motion, or Scheduled state on a returned task or event, with a widget self-check that sets any In motion or Scheduled row to Not started unless it names its task or event, and present unsourced exit criteria as suggested steps instead of asking. |
| `deal-review` | Synthetic Quick trace; [#26](https://github.com/salesforce/salesforce-skills/issues/26); [#24 follow-up](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032) | Select `totalCount` in the step 2 deal read. When it is above 1, run the documented candidate read; when it is above 10, first narrow the phrase with the account or other words from the request, never with a name from a returned deal. Take the one candidate whose name equals the requested deal, or else the one open candidate; otherwise list the candidates and ask, and when the list is empty or still cut off, ask for the full deal name or the account instead of listing a partial set. Keep the step 2 result only when it is the chosen deal; otherwise rerun the full read by Id. Add the `stages` root from `deal-advance-gap` to the step 1 read and take the stage tile's position and stages to close from it. |
| `deal-signals` | Synthetic Quick trace; [#25](https://github.com/salesforce/salesforce-skills/issues/25) | For a book or team sweep, return the step 5 digest instead of calling `display_widget`; for one named deal, render the widget without its chart-and-meter column, which needs a score and trend no step computes. Fire Stale commitment when a next step is set and `LastModifiedDate` is 21 or more days old. When an email tool is available, run the 2b email search; otherwise say email was not checked. List every flagged deal in the digest, grouping lower-priority ones if needed, and end with the ✅ line. |

Do not preserve unrelated local product changes during a refresh. A further deviation requires a
separate review and an explicit update to this allowlist.

## Synchronizing a new upstream version

1. Replace the active skill tree from the new upstream tree verbatim.
2. Confirm source and active skill inventories match exactly.
3. Reapply only the twelve patches above.
4. Generate `docs/portable-skill-diff-report.md`; it must show 22 exact matches and only the
   twelve allowed differences.
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
the official basic host and MCP Inspector. Quick rendering is verified for the local `calendar-events` correction and one `customer-health`
health assessment. A fresh health run after the
pre-dispatch safeguard completed without the earlier rewritten-query syntax error, and a later run confirmed
the case-total correction. Broader Quick coverage remains
unverified. See
[`evals/mcp_apps/README.md`](evals/mcp_apps/README.md).

## Validation

Run from `agent-plugin/`:

```bash
# Static packaging/frontmatter/query checks
python3 evals/validate.py

# Upstream renderer parity and approved contract exceptions
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
GET GraphQL/SOQL reads plus Configure's exact v63.0 Opportunity Full/View UI API layout read. It
rejects POST, non-query endpoints, GraphQL mutations, non-SELECT SOQL, and every other UI API
route before contacting Salesforce.

## Current verified baseline

- 34 active skills; 22 byte-identical to upstream and twelve approved deviations.
- Static validator: PASS.
- Live read fixtures on `genwatt-demo`: PASS.
- Exact skill calls on the synthetic `fresh` org: 157/157, with all six read-only guards passing.
- Active widget parity and hosted widget contracts: 26/26.
- Ravelin browser suite: 26/26 widgets, 130/130 semantic checks, and 59/59 captured
  actions (39 messages and 20 links), with no external effect.
