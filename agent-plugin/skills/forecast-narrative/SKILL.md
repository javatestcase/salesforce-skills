---
name: forecast-narrative
description: "Build a forecast-call brief from Salesforce opportunity aggregates, top-deal samples and field history, covering the number, bucket movement, risks and asks. Use to explain a rep or team's forecast; for a broader pipeline and coaching view, use team-pipeline."
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

# Forecast Narrative

Ground → aggregate the number + sample the deals (ONE turn) → narrative. Scope: my forecast (default), or a named rep/team. Period: current quarter (default). **Read-only:** this skill never writes to Salesforce; forecast submission and any field changes stay manual with the rep.

## 1. Ground (hardcoded — Opportunity only)

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's ForecastCategory/StageName picklists + any custom forecast/override `__c` fields — use exact names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

## 2. AGGREGATE the number, SAMPLE the deals — ISSUE BOTH IN ONE TURN

**Don't compute the number from a `first: N` page.** A raw pull caps at its page (`first: 200` returns 200 rows, not the book) — summing that page silently under-reports the total on a large book, and the first page isn't the whole set. Salesforce aggregates the totals server-side; use that for the number, and pull only a small bounded sample for the per-deal commentary.

`scope: MINE` = running user's book (no user lookup). `%QSTART%`/`%QEND%` = quarter's first/last day as explicit `YYYY-MM-DD` (never a quarter-relative literal — a bare `THIS_QUARTER` silently empties as boundaries move). Bound **both** ends of `CloseDate` — an open-ended `gte` pulls next-quarter+ deals into the current number. **Named rep/team:** swap `scope: MINE` for `OwnerId: { eq: "<UserId>" }`; for a team rollup, add `Owner { Name { value } }` to the sample so each deal attributes to its rep.

**2a. The number — aggregate by ForecastCategory (accurate at any volume).** One row per forecast bucket: count + $ sum. This is "The Number" table and it reconciles by construction — no page cap, no client-side sum of a truncated page.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { CloseDate: { gte: { value: \\\"%QSTART%\\\" }, lte: { value: \\\"%QEND%\\\" } } }, groupBy: { ForecastCategory: { group: true } }) { edges { node { aggregate { ForecastCategory { value } Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```
`ForecastCategory` maps to the buckets: **Closed** = Closed Won (in the bank), **Commit**, **Best Case**, **Pipeline**; **Omitted** = drop (closed-lost/omitted). Org doesn't populate `ForecastCategory` → swap `groupBy` to `StageName` and infer buckets from the stage map (ask once if unclear). **If the `aggregate` query errors** (some orgs throw `DataFetchingException` grouping a picklist) → don't re-fire the same shape; fall to the SOQL `GROUP BY` equivalent:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT ForecastCategory, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '%OWNERID%' AND CloseDate >= %QSTART% AND CloseDate <= %QEND% GROUP BY ForecastCategory" })
```
SOQL has no `scope: MINE`, so scope it by owner Id — without the `OwnerId` clause this fallback returns the whole org, not your book. `%OWNERID%` = the running user's Id for "my forecast"; resolve it with one `currentUser` read (needs **v66.0** — the GraphQL endpoint otherwise pins v65.0, so bump the version for this one call):
```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql", queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })
```
For a named rep/team, `%OWNERID%` is the `UserId` you already resolved for 2a's `OwnerId: { eq }` (or filter `Owner.Name` instead) — no `currentUser` lookup needed.

**2b. Sample the deals for commentary (bounded raw — Commit/Best Case lines).** The aggregate gives the number; this gives named deals to comment on. Cap hard (`first: 50`, biggest first) so it never overflows — this is a sample, not the book. Splice confirmed `__c` fields into `<OPP_CUSTOM>`. **Check `{` vs `}` balance before issuing** — splicing `<OPP_CUSTOM>` is where a brace drops.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"%QSTART%\\\" }, lte: { value: \\\"%QEND%\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } } }\"}" })
```

`InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry (once, with corrected text — never re-send identical text).

## 3. Bucket (in-prompt — no extra reads)

**The Number comes from 2a's aggregate** — count + $ per bucket (Closed Won / Commit / Best Case / Pipeline), whole-book and reconciled; drop the Omitted/closed-lost row. **Per-deal commentary comes from 2b's sample** — the top-by-Amount Commit and Best Case deals (the ones that matter for the call). Prefer `ForecastCategory`; else infer from `StageName` (never invent bucketing — infer from the org's stages or ask once). Say the per-deal lines are the top deals sampled, while the bucket totals are whole-book from the aggregate.

## 4. Changes + commentary

Prior snapshot pasted → diff it (up / slipped / added / lost). No snapshot → pull this quarter's field history for the delta (SOQL only — `OpportunityFieldHistory` has no GraphQL form), and only skip the section if that too is empty/unavailable:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT OpportunityId, Field, OldValue, NewValue, CreatedDate FROM OpportunityFieldHistory WHERE CreatedDate >= %QSTART%T00:00:00Z AND Field IN ('StageName','Amount','CloseDate') ORDER BY CreatedDate DESC" })
```
`CreatedDate` is a date-time field, so this filter needs a date-time literal: keep the `T00:00:00Z` after `%QSTART%`. A plain `YYYY-MM-DD` here fails with "must be of type dateTime".
Derive moved-up / slipped / added / lost from those rows. Per **Commit**/**Best Case** deal, one grounded line — status, what's needed, risk (cite `NextStep`/`LastActivityDate`). Link each deal. **Leader/team rollup across many reps:** cap per-deal commentary to top 5 by Amount per rep.

## 5. Output — forecast brief (primary, portable)

Assemble the brief as Markdown. This is the deliverable in any host. Cite each value; quote blank fields as blank rather than inventing.

```
# Forecast — <Scope> — <Period>

## The Number
| | $ | # |
|---|---|---|
| Closed Won | $<X> | <N> |
| Commit | $<X> | <N> |
| Best Case | $<X> | <N> |
| Pipeline | $<X> | <N> |
| **Commit Total** | **$<Closed+Commit>** | |

## Changes Since Last Week
- ⬆/⬇/✅/❌ <Deal> … (or "No prior snapshot — skipping delta")

## Commit Deals
- **<Account>** $<X> closing <Date> — <status, what's needed, risk>

## Best Case Deals
- **<Account>** $<X> — <what gets it to commit>

## Risk to Commit
- <Deal + specific risk + mitigation>

## On the Radar
- <Pipeline/Best-Case deals that could pull INTO the number if accelerated, or slip OUT — the upside/downside not yet in Commit>

## Asks
- <exec help / resourcing / unblocks>
```

**Concentration callout:** if a single deal is a large share (~40%+) of the Commit number, call it out explicitly — a single-deal quarter is a risk headline, not a footnote. Link each deal inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

For "what if <deal> slips?" scenarios, hand off to `deal-slip-scenario`. Submission stays manual with the rep.

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a meter/waterfall forecast visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
