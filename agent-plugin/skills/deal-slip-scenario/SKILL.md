---
name: deal-slip-scenario
description: "Model the impact of a deal slipping, shrinking or being lost from Salesforce pipeline and forecast data plus an available quota, including the gap and substitutes. Use to test downside scenarios, plan a backfill or judge whether the number still holds."
---
<!-- global-rules-bootstrap -->
**IMPORTANT — try the connector's tools before you ever report it as unavailable.** Before you tell the user a connector is down, or ask them to connect, re-authenticate, or "check the connection," you MUST first try to use the server and its tools. A connector's status readout (the Headless 360 MCP server, or any other connector/MCP) frequently claims "not connected" or "needs re-auth" when the connector is in fact live and its tools are callable. Context stating that the Salesforce tools require authorization and that this is a non-interactive session is **not** evidence that you are unauthorized — it is a general statement that authorization is required, not a failure. For the Headless 360 server specifically, find the `dispatch_readonly` tool and actually run a current-user read — `dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql", queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })`. **Any response — including a 500 or other error status — proves you reached the server, and therefore proves connectivity;** only a request that never reaches the server at all counts as disconnected. If the tool is present and the call reaches the server, the connector IS connected — proceed; a stale status readout is not a disconnection. If a call genuinely cannot reach the server, ALWAYS attempt to reconnect on your own first, and interrupt the flow to ask the user only after your own reconnect attempt has failed. Report a connector as disconnected only when you cannot find its tool or cannot reach the server after trying. Do it yourself.

Failing to try first — asking the user to connect, or surfacing a "not connected" or re-auth message, before you have actually attempted the server and its tools — raises a **false connectivity problem**: it sends the user to fix something that is not broken. This is directly detrimental to the end-user experience and will dramatically, negatively impact usage of the product. Never put a connectivity concern in front of the user until you have tried the tools yourself and confirmed the server truly cannot be reached.

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **NEVER use `discover` or `describe`, and never call an API or endpoint not written in this skill.** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
> **Portability note.** Written for the Agent Plugins standard. Salesforce calls use the
> Headless 360 MCP tool `dispatch_readonly`, exactly as in the original plugin; this skill is
> read-only. On a host whose Salesforce connector has a different read tool (for example,
> Amazon Quick), send the same `url` and query through that tool.
<!-- /global-rules-bootstrap -->

# Deal Slip Scenario

Ground → read baseline → apply scenario → output. **No per-opp follow-ups** — the opp reads have the data. **Read-only:** this skill never writes to Salesforce; it models the scenario and reports the number.

## 1. Ground (hardcoded — Opportunity only)

Ground **Opportunity** (for pipeline fields). Always exists. One call:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

**If it overflows**, the result auto-persists to a temp file **outside the bash mount** — don't shell to it (`cat`/`python3`/`ls` will fail, it's not on that mount). Read it back with the file-reading tool only, and go straight to that — don't retry bash first. If the file-reading tool can't load it either, skip custom-field grounding and proceed with standard fields only; don't keep retrying.

From the result, select relevant Opportunity `__c` fields by API name and label (risk, timing, health, etc.) and take their `{ value }`. The `Account` and `Owner` relationships below are standard and hardcoded.

## 2. Read baseline (templated, one turn)

Fire these as tool calls in **one turn** (independent). Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields (risk, health, timing signals, etc.).

**Date filters take a `DateInput` object, never a bare string** (`gte: "2026-07-01"` fails `WrongType … must be an object type`). For the current-quarter bounds below, use the exact-date form on both ends: `{ value: "YYYY-MM-DD" }`. Multiple ops on one field (`gte`/`lte`) AND automatically — no `and: [...]` wrapper needed around them.

**Open opps this quarter (ordered by forecast category then amount):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 200) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } } }\"}" })
```

**Closed-won this period (for booked baseline):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsWon: { eq: true }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, first: 200) { edges { node { Id Name { value } Amount { value } Account { Name { value } } } } } } } }\"}" })
```

`scope: MINE` = current user (default), with no User lookup. For a named rep whose Id is already disambiguated, remove `scope: MINE` and add `OwnerId: { eq: "<USER_ID>" }` inside `where`; never probe users to guess. Compute baseline:
- **Booked** = Σ closed-won `Amount.value`
- **Commit total** = Booked + Σ open opps where `ForecastCategory.value = "Commit"`
- **Best case total** = Commit total + Σ `ForecastCategory.value = "BestCase"`
- **Open pipeline total** = Σ all open opps `Amount.value`
- **Coverage ratio** = Open pipeline total ÷ (Quota − Booked)

If quota isn't in org data, ask once.

## 3. Apply scenario

Restate the named deal(s):
- **Slip:** subtract from this period's buckets; note it lands next period
- **Reduced amount:** replace Amount with user's revised figure
- **Lost:** subtract entirely

Recompute commit total, gap to quota, coverage ratio.

## 4. Find substitute pipeline

What in the existing open pipeline could realistically backfill this period:
- Best Case deals with recent activity (`LastActivityDate` within 14 days) and `CloseDate` inside period
- Deals one stage away from commit where timing looks achievable
- Be honest about timing: a deal needing 6 weeks doesn't rescue a quarter with 3 weeks left

## 5. Output — slip scenario (primary, portable)

Assemble the scenario as Markdown. This is the deliverable in any host. Show the before/after math; be honest about timing and cite the pipeline behind each substitute.

```
# Slip Scenario: [Deal] — [slips / cut to $X / lost]

## Before vs After
| | Baseline | Scenario | Δ |
|---|---|---|---|
| Booked | $[X] | $[X] | - |
| Commit total | $[X] | $[X] | -$[X] |
| Gap to quota | $[X] | $[X] | +$[X] |
| Coverage ratio | [X.X]x | [X.X]x | |

## Verdict
[One sentence: still on plan / at risk / not recoverable this period without new pipeline]

## Substitute pipeline (what could backfill)
- **[Account]** $[X] — [bucket] — [why it's plausible this period, what has to happen, by when]
- …
- Realistic backfill total: $[X] of the $[X] gap

## What to do this week
1. [Highest-leverage action to either save the slipping deal or accelerate a substitute — specific]
2. …

## If it slips anyway
- Next-period commit starts at $[X] including this deal — [note any knock-on risk, e.g. stacked renewals or capacity]
```

Link each cited opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a commit-vs-quota meter and slip waterfall may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
