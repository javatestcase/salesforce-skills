---
name: rep-context
description: "Catch a manager up on one of their sales reps before a 1:1: the rep's pipeline, recent activity, what they are working on, and where they need help, with suggested questions. Use when the person named is an internal rep, not a customer contact."
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

# Rep Context

Leader's 1:1 prep on one rep — pipeline, activity, where they're stuck. The named person is an INTERNAL rep (not a customer). Ground → read (pipeline + activity, one turn) → needs-help + questions. **Read-only:** this skill never writes to Salesforce; it produces context and suggested questions for the leader.

## 1. Ground + resolve the rep (one turn)

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's risk/health/next-step `__c` fields — use exact names. **Ground Opportunity and resolve the rep in one request** — `objectInfos` and the `User` resolver are independent `uiapi` siblings in the query below — then hold every rep-scoped read until `<REP_ID>` is resolved.

**Resolve the named rep to one active User.** If the manager supplied a Salesforce User Id, set `<REP_ID>` to it directly. Otherwise resolve a small active-User candidate set first — use the supplied name as a prefix (no leading `%`) in `<REP_PREFIX>`; for an email, swap the `Name` predicate for `Email: { eq: \"<REP_EMAIL>\" }`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } query { User(where: { Name: { like: \\\"<REP_PREFIX>%\\\" }, IsActive: { eq: true } }, orderBy: { Name: { order: ASC } }, first: 5) { pageResultCount pageInfo { hasNextPage } edges { node { Id Name { value } Email { value } Title { value } } } } } } }\"}" })
```
Auto-select `<REP_ID>` only when exactly one candidate returns, its `Name` exactly matches the supplied full name, and `hasNextPage` is false (for an email lookup, require one exact email match and `hasNextPage: false`). If `pageResultCount` is 0 or the match is ambiguous, show the returned names/emails/titles and ask the manager to choose or supply the full name, email, or User Id — **do not read the rep's book, activity, Slack, or calendar until `<REP_ID>` is resolved.**

## 2. Read the rep's book + activity (one turn, keyed on `<REP_ID>`)

Filter every read by `OwnerId: { eq: "<REP_ID>" }`. Splice confirmed `__c` fields into `<OPP_CUSTOM>`. **Check `{` vs `}` balance before dispatching.** This is a **Top 20 sample** for named deals — the pipeline totals come from the aggregate below, not from counting these rows.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { eq: \\\"<REP_ID>\\\" }, IsClosed: { eq: false } }, orderBy: { Amount: { order: DESC } }, first: 20) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Id } } } } } } } } }\"}" })
```

Fire this SOQL aggregate in the same turn, same owner + `IsClosed` filter as the sample above — it is the authoritative source for `Open: <N> opps, $<total> | by stage: <counts>`:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<REP_ID>' AND IsClosed = false GROUP BY StageName" })
```

In the SAME turn, fire the rep's recent activity — both Tasks AND Events (last 14d), plus this-quarter closed-won for the "This Q closed" number. These are independent reads keyed on the rep (not on each other), so batch all of them in this one turn — no added round-trip depth:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT COUNT(Id) cnt FROM Task WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_DAYS:14" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT COUNT(Id) cnt FROM Event WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_DAYS:14" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT SUM(Amount) amt, COUNT(Id) cnt FROM Opportunity WHERE OwnerId = '<REP_ID>' AND IsWon = true AND CloseDate = THIS_QUARTER" })
```

`<N> activities logged` = the Task `cnt` + Event `cnt` from the COUNT aggregates above. `InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry.

## 2b. Evidence (same turn — skip silently if absent)

- **Slack**: rep's posts in team/deal channels last 14d — blockers, asks, exec/deal-desk flags. (Ask once which channels if unknown.)
- **calendar**: external meetings last 14d + booked next 7d, if visible.

Use whatever Slack/calendar tools are available; skip silently if none are present (SF-only is fine). Cite source + date for anything you use.

## 3. Analyze (cite records/threads; invent nothing)

From pipeline + activity: largest opp with risk flags (stale LastActivityDate, blank NextStep, single-threaded = ≤1 contact role); any opp a Slack post flags a blocker on; coverage gap if pipeline thin; hygiene if many stale.

## 4. 1:1 questions

3–4 specific, grounded questions — not "how's pipeline" but "[Account] at [Stage] [N] days, you flagged a security review in Slack — where's that?"

## 5. Output — rep context (primary, portable)

Assemble the context as Markdown. This is the deliverable in any host. Cite the source per row; quote blank fields as blank rather than inventing.

```
# Rep Context: <Name>

## Pipeline
- Open: <N> opps, $<total> | by stage: <counts> | This Q closed: $<X> (<N> won)
- Top 3: **<Account>** $<X> <Stage> …

## Last 2 Weeks
- <N> activities logged; <N> external meetings (if calendar visible)
- Slack: <1–2 lines of what they raised — link threads>

## Likely Needs Help On
- **<Account>** $<X> — <specific flag + evidence>

## 1:1 Questions
1. <deal-specific, evidenced>

## Wins to Acknowledge
- <closed / advanced / notable from Slack>
```

Link each opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a pipeline/coaching visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
