---
name: call-prep
description: "Build a call brief from Salesforce meeting, account, opportunity, contact, and activity data plus email, documents, and Slack. Use before a customer meeting to understand attendees, deal history, open threads, and discovery needs; rep one-on-one: rep-context."
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

# Call Prep

Resolve meeting → ground → read account → (calendar + email + docs + slack searches, all in ONE turn with the SF read) → assemble brief. Qualification framework (BANT/MEDDIC/etc.), value prop, and competitors are external knowledge — infer from org data or ask once. Never invent. **Read-only:** this skill never writes to Salesforce; drafting is handed to `draft-outreach`/`call-follow-up`.

## 1. Resolve meeting

**Inputs:** a calendar event (by time, title, or "my next call"), OR an account name + time. If neither given, list today's external meetings and ask which one.

**1a. Find the owner (if named rep)**

- **"my next call"** (default) → skip to 1b with `scope: MINE`.
- **"[Rep]'s next call"** → resolve one User. Shared/demo orgs collide (one name → base user + regional variants). Pull enough to disambiguate:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Email { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id. **Several** → list them (Name · Email · active? · Id) and ask the user to pick. Then filter Events by `OwnerId: { eq: \"<UserId>\" }` in 1b.

**1b. Find the meeting**

Build the Event query based on input pattern. All patterns share the node shape (`Id Subject StartDateTime EndDateTime Location WhatId WhoId Description Who { ... on Contact { Id Name AccountId Account } } What { ... on Account { Id Name } ... on Opportunity { Id Name AccountId Account } }`). Combine filters with `and: [...]` when needed.

**Pattern: "my next call"** (scope: MINE, StartDateTime >= TODAY, first: 1):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { StartDateTime: { gte: { literal: TODAY } } }, first: 1, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Pattern: "[Rep]'s next call"** (OwnerId from 1a, StartDateTime >= TODAY, first: 1):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(where: { OwnerId: { eq: \\\"<UserId>\\\" }, StartDateTime: { gte: { literal: TODAY } } }, first: 1, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Pattern: specific event name** (e.g. "City of Hope call") — match Subject with LIKE, widen window to catch it (next 30 days), list if multiple:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { Subject: { like: \\\"%EVENTNAME%\\\" }, StartDateTime: { gte: { literal: TODAY }, lte: { range: { next_n_days: 30 } } } }, first: 10, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```
**One match** → use it. **Several** → list them (Subject · StartDateTime · Id) and ask user to pick. **Zero** → broaden `%EVENTNAME%` or ask user for account name directly.

**Pattern: time-based** (e.g. "call next thursday", "meeting tomorrow") — parse to date range. Use relative date filters:
- **"tomorrow"**: `StartDateTime: { gte: { range: { next_n_days: 1 } }, lte: { range: { next_n_days: 1 } } }`
- **"next thursday"**: compute day offset (if today = Monday, thursday = 3 days out) → `gte: { range: { next_n_days: 3 } }, lte: { range: { next_n_days: 3 } }`
- **"next week"**: `gte: { range: { next_n_days: 7 } }, lte: { range: { next_n_days: 14 } }`

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { StartDateTime: { gte: { range: { next_n_days: <OFFSET_START> } }, lte: { range: { next_n_days: <OFFSET_END> } } } }, first: 10, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```
**One match** → use it. **Several** → list them and ask user to pick.

**Pattern: account name directly** (e.g. "prep for City of Hope", "call with Acme") — no meeting specified. Skip Event query entirely, treat input as customer company name, jump to Step 2.

**Pattern: Event ID** (if user pastes SFDC Id `00U...`) — direct lookup:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(where: { Id: { eq: \\\"<EventId>\\\" } }, first: 1) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Extract:** title, time, `WhatId` (`001…` Account / `006…` Opportunity), `WhoId` (Contact), agenda (Description), meeting link (Location). From Description text or the `WhoId` email domain, identify the customer company.

## 2. Ground (hardcoded — Account only; fire with step 3 if independent)

Ground **only Account** — it always exists. Reveals this org's custom scalar and lookup signals; the standard relationships used below are hardcoded.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

Select relevant scalar Account `__c` fields (industry, size, qualification, etc.) and take their `{ value }`. For a relevant custom lookup, retain its exact `relationshipName` for step 3. `Owner`, `Opportunities`, and `Contacts` need no metadata. Complete this before step 3 because `<ACCOUNT_CUSTOM>` depends on it.

## 3. Read account (template — fill from step 2)

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = relevant confirmed custom lookups via their exact grounded relationship names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { <DOMAIN_FILTER> }, first: 1) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } Type { value } Description { value } <ACCOUNT_CUSTOM> <REL_BLOCKS> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } } } } Contacts(where: { Email: { in: [<ATTENDEE_EMAILS>] } }) { edges { node { Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```

Set `<ACTIVITY_ACCOUNT_FILTER>` from the resolved account identity: `AccountId: { eq: \"<AccountId>\" }` when you have the Id, or `Account: { Name: { eq: \"<ACCOUNT_NAME>\" } }` for direct name input. Run this activity read and the Account read **in the same turn** (independent once the account identity is known):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { recentTasks: Task(where: { <ACTIVITY_ACCOUNT_FILTER> }, orderBy: { ActivityDate: { order: DESC } }, first: 5) { edges { node { Id Subject { value } ActivityDate { value } Description { value } Status { value displayValue } Who { ... on Contact { Id Name { value } Title { value } Email { value } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } recentEvents: Event(where: { <ACTIVITY_ACCOUNT_FILTER> }, orderBy: { StartDateTime: { order: DESC } }, first: 5) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Description { value } Who { ... on Contact { Id Name { value } Title { value } Email { value } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Reference-field rule:** add scalar custom fields as `Field__c { value }`. Span a custom lookup only through its exact `relationshipName` from step 2. If a `<DOMAIN_FILTER>` matches more than one Account (shared/demo orgs collide), don't silently take `first: 1` — drop to `first: 10`, Account-level fields only, list the candidates, and ask the user to pick before reading further.

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

Independent of the SF result (they key on account name / attendee emails):
- **email**: threads with the attendee emails in the last 90d → last 2–3 exchanges (date, who, what was discussed/committed).
- **docs**: docs mentioning the account → prioritize "transcript"/"notes"/"plan" titles, most recent first. Read the top 1–2 and extract key topics, open questions, commitments.
- **slack**: account name in the last 30d → internal context (deal desk threads, exec mentions, escalations).

Use whatever email/doc/Slack connectors are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use. Do NOT fire extra SF dispatches for `Task`/`EmailMessage` — the step 3 reads plus external evidence have the data.

## 4. Attendee profiles

For each external attendee: their SFDC Contact title, plus a 1–2 line summary of what they likely care about (from title + prior interactions). Flag anyone new (not in SFDC Contacts, no prior thread).

## 5. Call plan

Based on opportunity stage and the qualification framework (inferred from org data or provided by the user):

- **Objective for this call:** what should be true after that isn't before.
- **3–5 discovery questions:** tailored to the stage and gaps in the framework; pull unanswered questions from prior notes.
- **Likely objections:** infer from prior conversations, or skip.
- **What to bring:** any doc/proposal/demo committed in prior threads.

## 6. Output — call brief (primary, portable)

Assemble the brief as Markdown. This is the deliverable in any host. Quote blank fields as blank rather than inventing; drop attendees/threads you have no data for.

```
# Call Prep: [Account] — [Meeting Title]
[Date Time] | [Attendees]

## Account Snapshot
- [Industry, size, type] | Owner: [Name]
- Open opp: **[Name]** — [Stage] $[Amount] closing [Date]
  Next step (SFDC): [NextStep or "blank"]

## Who's in the room
- **[Name]**, [Title] — [1–2 line context, prior interactions]
- **[Name]**, [Title] — ⚠ NEW (no prior contact)
…

## What's happened so far
- [Date] — [Last call summary from transcript]
- [Date] — [Email thread summary]
- [Date] — [Slack/internal context if any]

## Open threads
- [Unanswered question or commitment from prior notes]
…

## This call
**Objective:** [one sentence]

**Questions to ask:**
1. [Stage-appropriate discovery Q]
…

**Likely objections:** [list]

**Bring:** [any committed deliverables]
```

Link the opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

## 7. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), an attendee/talk-track visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 6 is the whole deliverable.
