---
name: team-pipeline
description: "Build a team pipeline brief from Salesforce users and opportunities, showing closed revenue, forecast, swing deals and coaching needs by rep. Use to review a manager's team, prepare a pipeline meeting or find where reps need help. One rep: pipeline-review."
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

# Team Pipeline

Ground → resolve team → read opps → analyze → output. **No per-opp SF follow-ups** — the team opps read has the data. **Read-only:** this skill never writes to Salesforce; it produces a scoreboard and coaching prompts for the leader.

## 1. Ground (hardcoded — User + Opportunity)

Ground **User** (for team resolution) and **Opportunity** (for pipeline fields). Both always exist. **Fire as two separate calls, not one combined call** — combined User+Opportunity ObjectInfo commonly exceeds the tool's char limit. Same turn, same shape, one `apiNames` each:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"User\\\"]) { fields { ApiName label dataType relationshipName } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label dataType relationshipName } } } }\"}" })
```

If either result is unwieldy, skip custom-field grounding for that object and proceed with standard fields only; don't keep retrying. From the result: (a) scalar `__c` fields (quota, forecast, risk, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's Name.

## 2. Resolve team

**"my team"** (default) — reps where Manager = current user:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { and: [{ ManagerId: { eq: \\\"<CURRENT_USER_ID>\\\" } }, { IsActive: { eq: true } }] }, first: 50) { edges { node { Id Name { value } Email { value } <USER_CUSTOM> } } } } } }\"}" })
```

**A named list, role, or territory** (disambiguate — do NOT probe): shared/demo orgs collide hard on name (one name → base user plus regional variants like `(AM)`/`(BK)`/`(SG)`). Pull enough to disambiguate at a glance — never pull each candidate's pipeline to guess which is real:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } IsActive { value } } } } } } }\"}" })
```

**One match per name** → take its Id. **Several** → list them (Name · Title · active? · Id) and ask the user to pick; the suffix/title is usually the tell. Don't guess.

Insert `<USER_CUSTOM>` = confirmed scalar `__c { value }` fields (quota, etc.). Capture the Ids — they become the owner filter in step 3.

## 3. Read team opps — AGGREGATE the rollup, SAMPLE the top deals, ISSUE ALL IN ONE TURN

**Do not pull the whole team's book as raw records.** A team of 5+ reps with 200 open opps returns well past the point a tool result overflows. Salesforce aggregates server-side — use it for the scoreboard math; only a small, bounded sample of concrete deals comes back as raw records, for swing-deal specifics and at-risk flags.

Fire these as tool calls in **one turn** (independent, all filtered by the team-user Ids from step 2). Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields (risk, coaching signals, etc.) on the sample query only — aggregates don't need them.

**Date filters take a `DateInput` object, never a bare string** (`gte: \"2026-07-01\"` fails `WrongType … must be an object type`). For the current-quarter bounds below, use the exact-date form on both ends: `{ value: \"YYYY-MM-DD\" }`. Multiple ops on one field (`gte`/`lte`) AND automatically — no `and: [...]` wrapper needed around them.

**Rollup by forecast category (GraphQL aggregate — folded into the top-N sample request below).** `ExpectedRevenue` (Amount × Probability, a standard field) sums straight to the Weighted column — no client-side probability math. This rollup rides in the sample query (below) as an `aggregate` sibling of the detail read — one dispatch returns both. It yields one row per rep × forecast category. Per rep: Commit $ = that rep's `Commit`-category `Amount.sum`; Best-case $ = the `BestCase` row; Weighted = Σ `ExpectedRevenue.sum` across that rep's rows.

**Closed-won this period, per rep (GraphQL aggregate).** Feeds the scoreboard's Closed column:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsWon: { eq: true }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } Amount { sum { value } } } } } } } } }\"}" })
```

**Top-N sample per rep + forecast-category rollup (ONE request).** The rollup gives the scoreboard numbers; the sample gives named deals for the swing-deal writeups, at-risk flags, hygiene flags, and Monday questions below. Cap the sample hard (`first: 60`, biggest first) so it never overflows — this is a sample, not the book. **`orderBy` takes only ONE field** — a multi-field array (`orderBy: [{...},{...},{...}]`) fails `WrongType ... must be an object type`; sort by `Amount` alone and group by owner client-side from the `Owner.Name` on each row. The forecast-category rollup rides in this same request as an `aggregate` sibling of the sample — read the per-rep Commit/Best-Case/Weighted numbers from its edges, the named deals from the sample rows.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 60) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } CreatedDate { value } Probability { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, groupBy: { OwnerId: { group: true }, ForecastCategory: { group: true } }) { edges { node { aggregate { OwnerId { value } ForecastCategory { value } Id { count { value } } Amount { sum { value } } ExpectedRevenue { sum { value } } } } } } } } }\"}" })
```

Map each row's `OwnerId` → rep name using the User list from step 2 — no extra lookup needed.

**If a GraphQL `aggregate` query errors** (some orgs throw grouping a picklist/Id field), don't retry the same shape — fall to the SOQL `GROUP BY` equivalent, which groups cleanly. **For the combined sample request specifically**, the grouped `aggregate` sibling (`OwnerId`/`ForecastCategory`) can take the whole request down with it — re-fire the sample as the detail `query` alone (drop the `aggregate` block) to keep the named deals, and get the per-rep rollup from this SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT OwnerId, ForecastCategory, COUNT(Id) cnt, SUM(Amount) amt, SUM(ExpectedRevenue) weighted FROM Opportunity WHERE OwnerId IN (<TEAM_USER_IDS>) AND IsClosed = false AND CloseDate >= <Q_START> AND CloseDate <= <Q_END> GROUP BY OwnerId, ForecastCategory" })
```
(Closed-won the same way: swap `IsClosed = false` for `IsWon = true` and drop the `ForecastCategory` group.)

**Hygiene counts (GraphQL aggregate, full book — feeds step 6, not sample-limited).** The top-60 sample above skews toward the biggest deals; these three counts cover every open opp so stale/overdue/blank-NextStep flags aren't undercounted. `<STALE_CUTOFF>` = today − 14 days, `<TODAY>` = today, both as `DateInput` (`{ value: "YYYY-MM-DD" }`):
```
-- Stale 14d+, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, LastActivityDate: { lte: { value: \\\"<STALE_CUTOFF>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })

-- Past CloseDate, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { lt: { value: \\\"<TODAY>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })

-- Blank NextStep, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, NextStep: { eq: null } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })
```
Fire these in the same turn as the rollup/closed-won/sample queries above. If `aggregate` errors on any of the three, fall to SOQL `COUNT(Id) ... GROUP BY OwnerId` with the matching WHERE (same fallback pattern as the rollup above).

**Perf guardrail:** Do NOT fire per-opp SF follow-ups (`EmailMessage`, `Task`, `OpportunityFieldHistory`) — the rollups + sample above already have the data. Email/doc/Slack searches for flagged accounts only (step 3b).

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

**Issue step 3 and step 3b as tool calls in a single turn.** Fire searches for top 3–5 at-risk accounts only (keyed on account name, not the SF result):
- **slack**: internal mentions in team channel (if configured) → reps already flagging something.

Use whatever Slack search tools are available. If none present, skip silently. Cite source + date for anything you use.

## 4. Per-rep scoreboard

For each rep, compute and assign a one-word **Call**:

| Rep | Closed | Commit | Weighted | vs Quota | Call |
|---|---|---|---|---|---|

- **Weighted** = sum of (Amount × Probability/100) across open opps.
- **Call** = Ahead (closed ≥ quota or weighted comfortably covers gap) / On-track / Behind.
- Tip: if a rep's Commit > Weighted, their stages are probably optimistic — challenge it.

If quotas aren't in SFDC, ask once and remember for the session.

## 5. Deals that decide the quarter

Identify the 3–5 opps that swing the number: large Amount × late stage × rep-needs-it × closing this period. For each, write three lines:

- **Why it matters:** [the math — "$X is N% of [rep]'s gap"].
- **Risk:** [specific thing that could kill it, from evidence].
- **Do this:** [one concrete leader action — "ask [rep] when they last talked to procurement; offer to send exec note if it's been 5+ days"].

The "do this" is the point. Be specific enough that the leader can act without further research.

## 6. Team-level flags

- **At-risk Commit deals:** any Commit-category deal with risk flags — these threaten the number.
- **Coaching signals:** reps with high stale-% (from the hygiene aggregates above, full book) or low coverage.
- **Hygiene:** reps ranked by the stale/past-CloseDate/blank-NextStep aggregate counts (full book, not the sample) — name specific accounts from the top-60 sample where they overlap.
- **Big swings:** deals >2x average that could make or break the quarter.

## 7. Monday questions

For each Behind or At-risk rep, write ONE question phrased the way the leader would actually ask it in a 1:1 or Slack. Grounded in a specific deal, conversational, not interrogative. Examples: "where's the [Account] security review at — saw it's been a couple weeks" / "do you need anything from me on [Account] or is it just waiting on them."

Search Slack for each rep's recent posts in the team channel from config — if they already flagged something, reference it instead of re-asking.

## 8. Output — team pipeline brief (primary, portable)

Assemble the brief as Markdown. This is the deliverable in any host. Reconcile the scoreboard totals with the detail rows; cite the source per row; quote blank fields as blank.

```
# Team Pipeline — [Period]
Target $[X] | Closed $[X] | [N] days left

## Scoreboard
| Rep | Closed | Commit | Weighted | Gap | Call |
|---|---|---|---|---|---|
| [Name] | $[X] | $[X] | $[X] | $[X] | Behind |
…
| **Team** | **$[X]** | **$[X]** | **$[X]** | **$[X]** | |

## Deals That Decide the Quarter
**[Account]** — $[X], [Stage], [Rep]
  Why it matters: [the math]
  Risk: [specific, evidenced]
  → **Do this:** [one concrete leader action]

[repeat 3–5x]

## Risk Flags
- Pushed dates: [N] opps moved CloseDate this week
- Stale 14d+: [N] opps — [Account, Account, …]
- Past close date: [N] opps need hygiene before the call

## Monday Questions
- **[Rep]:** "[one question, conversational, deal-grounded]"
- **[Rep]:** "[…]"

## If you want to dig
- Per-rep detail: ask "just [rep name]"
- Full at-risk list: run pipeline-review with team scope
```

Link each opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

## 9. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a by-rep scoreboard and pipeline-by-stage visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 8 is the whole deliverable.
