---
name: pipeline-review
description: "Build one rep's current pipeline assessment from Salesforce stage aggregates, deal samples and closed-deal history, covering coverage, hygiene and risks. Use when reviewing pipeline health and stage distribution; for changes over time, use deal-signals."
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

# Pipeline Review

Ground → resolve scope → (aggregate the book + sample the top deals, ONE turn) → assemble + flag → output. This is one rep's pipeline — for "my team's pipeline" use team-pipeline; for "what changed" use deal-signals. **Read-only:** this skill never writes to Salesforce; it surfaces findings and links records for the rep to act on. Resolve scope to one owner before the read; if a named rep is ambiguous, ask — don't guess or probe. Reconcile headline totals with the detail rows.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's stage/risk/activity `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. Note scalar `__c` fields worth rolling up (stage-entry date, risk, health, forecast). Grounding is best-effort (customs are additive); if the metadata can't load, take the standard fields and move on. Stage buckets come from the `StageName` values the reads return; standard fields, `Account`/`Owner` spans, and `OpportunityContactRoles` are reliable across orgs.

## 1b. Resolve scope

- **"my pipeline"** (default) → add `scope: MINE` to the query root — no user-Id lookup.
- **named rep** → resolve one User. Pull enough to disambiguate at a glance — shared/demo orgs collide hard (one name → base user plus regional variants like `(AM)`/`(BK)`/`(SG)`):
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id. **Several** → list them (Name · Title · active? · Id) and ask the user to pick; the suffix/title is usually the tell. Don't pick or probe their pipelines to guess. Then filter opps by `OwnerId: { eq: "<UserId>" }`.
- **team** → out of scope; hand to team-pipeline.

## 2. Read (fill from step 1) — AGGREGATE the book, SAMPLE the top deals, ISSUE ALL IN ONE TURN

**Do not pull the whole book as raw records.** A rep with 100+ open opps returns 75KB+, which overflows the tool result. Salesforce aggregates server-side — use it. The stats come from aggregate rows (a handful, not hundreds); only a small, bounded sample of concrete deals comes back as raw records.

Fire these as tool calls in **one turn** (independent). Insert `<OPP_CUSTOM>` = confirmed `__c { value }` fields on the sample query only (aggregates don't need them).

**2a. Whole-book rollup by stage (GraphQL aggregate — folded into the 2b request).** No `CloseDate` filter for a health view — a `THIS_QUARTER` filter silently drops deals as quarter boundaries move. If the user names a period, add explicit `CloseDate: { gte: … lte: … }`. This rollup rides in the 2b query as an `aggregate` sibling of the sample (one dispatch returns both); it yields one row per stage — stage name, count, $ sum — the by-stage table and the open total (Σ), with no extra record pull.

**2b. Top-N sample per stage + whole-book stage rollup (ONE request).** The rollup gives the shape; the sample gives named deals to point at. Cap the sample hard (`first: 40`, biggest first) so it never overflows — this is a sample, not the book. Order by `Amount DESC`; take the top few per stage when you present. The 2a stage `aggregate` rides in this same request as a sibling of the sample — read the by-stage counts/sums and open total from its `aggregate` edges and `totalCount`, the named deals from the sample rows.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, first: 40, orderBy: { Amount: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } NextStep { value } LastActivityDate { value } Type { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Id } } } } } } } aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

**2c. Closed-baseline win rate (GraphQL aggregate, last full quarter).** Counts grouped by won/lost — no record pull, zero date math (`eq: { literal: LAST_QUARTER }`; widen only if asked):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: LAST_QUARTER } } }, groupBy: { IsWon: { group: true } }) { edges { node { aggregate { IsWon { value } Id { count { value } } Amount { sum { value } } } } } } } } }\"}" })
```

**2d. Whole-book hygiene by stage (GraphQL aggregate).** Blank-`NextStep` count per stage across the entire book — so the hygiene finding is book-wide, not "among the top 40 sampled". No date math:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, NextStep: { eq: null } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } } } } } } } }\"}" })
```
(Same `OwnerId` swap for a named rep. A stale-by-stage rollup is also expressible with a computed `LastActivityDate: { lt: "<today−14d>" }` cutoff grouped by StageName — but null-activity rows won't match `lt`, so it under-counts never-touched deals; blank-NextStep is the clean whole-book signal.)

**Named rep** → swap every `scope: MINE` for `OwnerId: { eq: \"<UserId>\" }`. **Empty** 2a `edges`/`totalCount: 0` → no open pipeline for this scope; say so plainly, skip the rest.

**If a GraphQL `aggregate` query errors** (some orgs throw `DataFetchingException` grouping a picklist/Id field), don't retry the same shape — fall to the SOQL `GROUP BY` equivalent, which groups picklists cleanly. **For the 2b combined request specifically**, the grouped `aggregate` sibling (`StageName`) can take the whole request down with it — re-fire 2b as the detail `query` alone (drop the `aggregate` block) to keep the sample, and get the by-stage rollup from this SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE IsClosed = false AND OwnerId = '<UserId>' GROUP BY StageName" })
```
(Own scope → resolve the current user's Id first, or filter by `Owner.Name`; SOQL has no `scope: MINE`.) Win rate the same way: `SELECT IsWon, COUNT(Id) cnt FROM Opportunity WHERE IsClosed = true AND CloseDate = LAST_QUARTER AND OwnerId = '<UserId>' GROUP BY IsWon`.

## 3. Assemble + flag (record only; reconcile totals; invent nothing)

- **By stage** — straight from 2a's aggregate rows: count, $ sum per stage. Σ of stage $ = open total (they come from the same query, so they reconcile by construction). **Blank-NextStep per stage is whole-book from 2d** — report those counts as book-wide. Staleness/aging per-stage aren't in an aggregate; report those from the 2b sample and **say they're "among the top N sampled," not whole-book**.
- **Top deals per stage** — from the 2b sample, name the biggest 2–3 opps in each stage (Account · $ · close · next-step state · type) so the rep sees concrete deals, not just totals.
- **At-risk opps** — from the 2b sample, flag any that hit: stale (no activity 14d+) · past `CloseDate` · blank `NextStep` · **single-threaded (`OpportunityContactRoles` edge count ≤ 1)**. **If a flag matches nearly the whole sample** (common in lightly-maintained orgs), report it once as a **systemic finding** — use 2d's book-wide blank-NextStep count for that line ("next-step blank on N of M open — hygiene gap") — and rank the at-risk list by $, rather than dumping dozens of identical-looking rows.
- **Coverage** — weighted open pipeline (from 2a totals × stage probability if grounded, else raw open $) vs quota (only if the user gives one) or vs last-quarter closed $ from 2c; 3× remaining-gap heuristic; note if under.
- **Velocity** — from 2c: win rate = won ÷ (won+lost) counts. **Cycle time / median: don't compute it** — no API supports median or date subtraction, and reconstructing it means pulling every closed record (the overflow we're avoiding). Only report an average cycle if grounding surfaced a numeric sales-cycle `__c` field you can `avg` in the aggregate. Stage→stage conversion needs stage history; omit — don't fabricate.

## 4. Output — pipeline review (primary, portable)

Assemble the review as Markdown. This is the deliverable in any host. Reconcile the totals; quote blank fields as blank rather than inventing. Any win-rate value is a 0–100 percentage computed as `won_count ÷ (won_count + lost_count) × 100`; if either count is unavailable, omit the win-rate line.

```
# Pipeline Review — <Scope> — <Period>

## Summary
Open: <N> opps, $<total> · weighted $<weighted> · coverage <N>× <✅ / ⚠ under 3×> · at-risk <N>, $<sum>

## By stage (whole book)
<Stage> · <N> opps · $<sum>
…  (Σ stage $ = $<total>, Σ opps = <N> — from the rollup)

## Top deals per stage (sampled, biggest first)
<Stage>: <Account> $<X> close <Date> · <next-step state> · <Type>; <Account> $<X> close <Date> …
… (name the biggest 2–3 opps per stage — the sample holds them)

## At-risk (from sample, biggest first)
<Account> · <Stage> · $<X> · close <Date> · <flags> → <action>
…  (Σ at-risk $ = $<sum>)
[If a flag hits nearly all sampled: one line — "Systemic: next-step blank on all <N> sampled — hygiene gap", don't list every row.]

## Conversion Signal (last-Q baseline)
Win rate <N%> (won <N> ÷ won+lost <N>, from 2c)[ · avg cycle <N>d only if a cycle-days field was grounded]. Stage→stage conversion needs stage history — omit, don't fabricate.

## Focus
1. Highest-$ at-risk + action
2. Biggest / most-exposed stage + action
3. Coverage gap if under 3×
```

Link each opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

## 5. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a by-stage/coverage-meter visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 4 is the whole deliverable.
