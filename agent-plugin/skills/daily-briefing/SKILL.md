---
name: daily-briefing
description: "Create today's sales briefing from Salesforce events, near-term and overdue deals, account context, commitments, and unread customer email. Use for a morning rundown combining meetings, pipeline, and inbox priorities; schedule-only requests: calendar-events."
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

# Rules

- Parallelize everything independent. This is a morning routine — speed matters; fire the running-user lookup, calendar, closing-soon, past-due, their two totals, and inbox in ONE turn.
- **Totals come from Salesforce, not arithmetic.** Show counts and dollar totals only from the aggregate reads in step 2; never sum or count rows yourself.
- **Read-only.** This skill never writes to Salesforce. It surfaces and links records; drafting/sending is handed off to other skills (e.g. `inbox-sweep`, `draft-outreach`).

# Daily Briefing

Ground → (calendar + closing-soon + past-due + inbox, ALL in ONE turn) → match meetings to accounts (one batched turn) → flag → output. This is today's rundown, not a pipeline review — closing-soon is a small bounded set, so pull concrete rows, don't aggregate.

## 1. Ground (hardcoded — Opportunity only; fire with the step-2 batch)

Ground **only Opportunity** — it always exists. Reveals this org's stage/next-step/activity `__c` names so the closing-soon read can surface them; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. On customized orgs the response can be large; filter to `__c` fields whose `label` matches your keywords. Standard fields (`Amount`, `CloseDate`, `StageName`, `NextStep`, `LastActivityDate`) and `Account`/`Owner` spans are reliable across orgs.

## 2. Read — running user + calendar + closing-soon + past-due + inbox, ALL IN ONE TURN

Five independent reads plus two section-total aggregates (plus step 1) — batch them in a single turn. Insert `<OPP_CUSTOM>` = confirmed `__c { value }` fields from step 1.

**2a. Today's calendar** — today's meetings for the running user. Read the calendar from the `Event` object via GraphQL (below), or a dedicated calendar connector if one is present. Do NOT guess a REST path.

`Event.What`/`Event.Who` are polymorphic and expose no `Name` span — pull the raw `WhatId`/`WhoId` scalars. A `001…` `WhatId` is an Account, `006…` an Opportunity — resolve it in step 3.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { ActivityDate: { eq: { literal: TODAY } } }, first: 50, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } } } } } } }\"}" })
```

`scope: MINE` returns events you own. Invitee-only meetings live under `EventRelation` and may not appear — an empty calendar usually means that or a genuinely clear day, not a failure; say which.

**2b. Closing soon** — the rep's open opps closing in the next 14 days. Pull concrete rows (`first: 50`), not an aggregate. Date filters take a `DateInput` object, never a bare string. "Closing in the next 14 days" = `CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 14 } } }`:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 14 } } } }, first: 50, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } } } } } } }\"}" })
```

**2c. Past due** — the rep's open opps with a close date in the past (still not closed):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { lt: { literal: TODAY } } }, first: 50, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } } } } } } }\"}" })
```

**2b-total / 2c-total. Section totals** — the count and `Amount` sum for 2b and 2c, computed by Salesforce. Issue both in the same turn as 2b/2c. Each MUST use the exact same `scope` and `where` as its row read, or the totals won't match the rows:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 14 } } } }) { edges { node { aggregate { Amount { sum { value displayValue } } Id { count { value } } } } } } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { lt: { literal: TODAY } } }) { edges { node { aggregate { Amount { sum { value displayValue } } Id { count { value } } } } } } } } }\"}" })
```

**Totals rule:** every count or dollar total you show comes from these aggregate reads, quoted as returned (use `displayValue`). Never add up or count rows yourself. The aggregates cover every matching record, while the row reads stop at `first: 50`, so when the count is larger than the rows you have, say so: "showing [rows] of [count]". If an aggregate read fails, show the rows without a total and say the total is unavailable.

**2d. Inbox signal** — unread email from the last 48h whose sender domain matches an account you own (email connector). Sender, subject, domain only — don't read bodies (that's `inbox-sweep`).

**2e. Running user** — who the briefing is for, their name, and timezone. `currentUser` needs no Id and requires **v66.0** (bump the version in the URL for this one call):

```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id Name { value } Email { value } TimeZoneSidKey { value } } } }\"}" })
```

Use `Name` for the header; `TimeZoneSidKey` to render "today" and last-touch ages in the rep's zone; `Email` domain as a fallback when matching your own account inbox in 2d.

## 3. Meeting context — ONE batched turn (depends on 2a's WhatIds/domains)

Resolve every meeting's account in **one** query, OR-ing two kinds of match: (a) any `WhatId` from 2a that is an Account (`001…`) → `Id: { eq }`, or an Opportunity (`006…`) → its `AccountId`; (b) external-attendee email domains → `Website` `like`. Prefer the direct `WhatId` link; fall back to domain match only when there's no usable `WhatId`.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { or: [ { Id: { in: [\\\"<WhatId account 001…>\\\"] } }, { Website: { like: \\\"%domain1%\\\" } }, { Website: { like: \\\"%domain2%\\\" } } ] }, first: 25) { edges { node { Id Name { value } Website { value } LastActivityDate { value } Opportunities(where: { IsClosed: { eq: false } }, first: 5, orderBy: { Amount: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } } } } }\"}" })
```

In the same turn, per matched account: a **docs** search (most recent transcript/notes/plan — title + one line) and a **"you owe them"** email search (sent-mail promises still unfulfilled). No account match → `(no CRM match — net new or personal)`.

## 4. Flag (record only; cite; invent nothing)

- **Closing soon** — flag blank `NextStep` or stale (`LastActivityDate` 7d+).
- **Inbox** — count customer-domain unreads; list the top 3 by matched-opp `Amount`.
- **Per meeting** — time · title · attendees · account · open-opp stage+$ · last touch · one-line "why it matters" · **you owe** (or "nothing outstanding") · **walk in asking** (the one thing to get, given stage + context).

## 5. Output — structured briefing (primary, portable)

Assemble the briefing as Markdown. This is the deliverable in any host. Omit any section you have no data for; never emit placeholder tokens or empty lists.

```
# Daily Briefing — [Date]

## Today's Meetings ([N])
[Time] **[Title]** — [Attendees]
  Account: [Name] · Opp: [Stage] $[Amount] closes [Date] · Last touch: [N]d ago[ · context from doc]
  You owe: [unfulfilled promise, or "nothing outstanding"]
  → Walk in asking: [the one thing]
…

## Closing in 14 Days ([count] opps, [sum displayValue][ · showing [rows] of [count]])
- **[Account]** — [Stage] $[Amount] closes [Date] · Next: [NextStep or "⚠ BLANK"] · Last activity: [N]d[ "⚠ 7+d stale"]
…

## Past Due ([count] opps, [sum displayValue][ · showing [rows] of [count]])
- **[Account]** — [Stage] $[Amount] closed [Date] ([N]d past) · Next: [NextStep or "⚠ BLANK"]
…

## Inbox ([N] unread from customers)
- [Sender] @ [Account] — "[Subject]" (opp $[Amount])
…  Run `inbox-sweep` to triage and draft replies.
```

Lead with the single highest-priority move for the day (the meeting or deal that most needs attention) as a one-line callout above the sections.

Section `[count]` and `[sum displayValue]` come from the 2b-total / 2c-total aggregate reads (see the totals rule in step 2). Add "showing [rows] of [count]" only when the aggregate count is larger than the number of rows listed.

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (for example, Amazon Quick dashboards or Apps in Quick), a visual briefing layout may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill: see the plugin's host-extension directory (`com.salesforce.quick/ui`) for the Quick rendering guidance and templates. When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
