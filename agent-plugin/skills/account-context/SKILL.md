---
name: account-context
description: "Build a 360-degree brief on a company already in Salesforce: CRM state, key contacts, recent email, documents and internal Slack. Use when asked to tell about, catch up on, or give the full picture on an existing account. Not in CRM: research-prospect."
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

# Account Context

Assemble a 360° brief on an account — the Salesforce record, open pipeline, key contacts, recent activity, and (when connected) email, documents, and internal Slack — in one pass. Resolve to one account, ground its customs, one read by Id, enrich in parallel, synthesize. **Read-only:** this skill never writes to Salesforce; drafting is handed to `draft-outreach`/`call-follow-up`.

## 1. Resolve the account (disambiguate — do NOT probe)

Shared/demo orgs collide on name (duplicate seed data, empty test records like `MBourlon Acme Lab`). Land on a single Id first. One small query, **Account-level fields only** — never pull each candidate's Opportunities/Contacts to see "which is real"; that's a probe, skip it unless the user asks. If the user gave a Salesforce Id, skip this step.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 10) { edges { node { Id Name { value } Website { value } Type { value } Industry { value } LastActivityDate { value } Owner { Name { value } } } } } } } }\"}" })
```

(domain → filter `Website` instead of `Name`.)

- **One clear match** → take its Id, continue.
- **Several plausible matches** → list them (Name · Website · Owner · LastActivityDate · Id link) and ask the user to pick. `LastActivityDate` is your one free liveness tell — a blank/stale row beside a recent one usually flags the dead test record — but let the user decide; don't pick for them.
- **10 rows hit (likely more)** or **empty** → ask the user to narrow or correct the name.

## 2. Ground customs (fire in parallel with step 1)

Get the `__c` fields on every object this read touches — Account (health, tier, segment, ARR, renewal, status, score, region), Opportunity (forecast, competitor, close-plan, deal-health), Contact (buyer role/persona), Task (activity customs) — so the read can fetch them. Standard fields and the standard children (`Opportunities`, `Contacts`, `Tasks`) are reliable across orgs; you're grounding **only** for customs worth showing.

Issue these four individual reads in the same turn, in parallel with step 1. Keep one object per `objectInfos` request; combining catalogs can overflow the tool result.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Task\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

**An individual response can still be huge** — person-account orgs add hundreds of `__pc` fields, managed packages add `namespace__` fields (60KB+). Scan for `__c` fields whose `label` matches your signal keywords, ignoring `__pc` and `namespace__` noise. Grounding is best-effort: if a catalog is still unwieldy, take the standard fields and move on — customs are additive, not required.

## 3. Read the resolved account (by Id — fill from steps 1–2)

Filter by the resolved `Id` (disambiguation is done — no `like`, no `first:1` roulette). Insert the per-object custom tokens from step 2's grounding — `<ACCT_CUSTOM>` on Account, `<OPP_CUSTOM>` on each Opportunity node, `<CONTACT_CUSTOM>` on each Contact node, `<TASK_CUSTOM>` on each Task node — each = that object's confirmed `__c { value }` fields (`{ value displayValue }` for currency/picklist). Omit a token if grounding surfaced no relevant customs for that object.

Preserve the supplied GraphQL documents; replace only `<ID>` and the grounded custom-field placeholders.

**Rules that avoid the retry loop:**
- Related record's name → span the lookup: `Owner { Name { value } }`. `Account.Owner` and `Opportunity.Owner` are single-target (→ `User`) and span cleanly. Never append `{ … }` to a raw `Id`/`__c` field.
- **Activity owners are polymorphic — don't span them.** `Task.Owner`/`Event.Owner` (and `Who`/`What`) are `User | Group` unions, so `Owner { Name { value } }` fails with `Field 'Name' in type 'Task_Owner' is undefined`. The default query below omits the owner span on Tasks; if you truly need it, use a fragment — `Owner { ... on User { Name { value } } }`. Don't assume symmetry with Opportunity.
- **Any `FieldUndefined` / `undefined in type X`** means that name or shape is wrong for THIS org — don't re-fire it. Re-ground that one object via `objectInfos(apiNames:["<Obj>"]) { fields { ApiName relationshipName referenceToInfos { ApiName } } }` (a `referenceToInfos` listing 2+ targets = polymorphic union → use a fragment), then retry from confirmed names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ID>\\\" } }, first: 1) { edges { node { Id Name { value } Website { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } Type { value } BillingCity { value } BillingCountry { value } Description { value } CreatedDate { value } LastActivityDate { value } Owner { Name { value } Email { value } } <ACCT_CUSTOM> Opportunities(first: 10, where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } Type { value } LastActivityDate { value } <OPP_CUSTOM> Owner { Name { value } } } } } Contacts(first: 15, orderBy: { LastActivityDate: { order: DESC } }) { edges { node { Id Name { value } Title { value } Email { value } Phone { value } LastActivityDate { value } <CONTACT_CUSTOM> } } } Tasks(first: 10, where: { ActivityDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } Description { value } <TASK_CUSTOM> } } } } } } } aggregate { Opportunity(where: { AccountId: { eq: \\\"<ID>\\\" }, IsClosed: { eq: false } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

`Opportunities` is bounded open supporting detail; the `aggregate` block rides in the same query (one dispatch) and is authoritative — use `totalCount` and `Amount.sum.value` for the complete open pipeline, not the ten supporting-detail records. `Tasks` carries **no** `Owner` span (polymorphic — see rule above). If a child errors, drop that block and read recency from `LastActivityDate` — don't retry.

## 4. Enrich (parallel — skip any source not connected; never fabricate)

Fire these together in one turn; skip any whose tool isn't available and note it once at the end.
- **Email** — threads to/from the account's domain, last 90d. 5 most recent: date, participants, subject, one-line landing.
- **Documents** — docs mentioning the account: most recent transcript/notes + any account plan / proposal / MSA (title + date + one-line).
- **Slack** — account name, last 60d: relevant threads (deal desk, escalations, exec mentions, win/loss) with links.

## 5. Output — account brief (primary, portable)

Assemble the brief as Markdown. This is the deliverable in any host. Lead with current state, not raw data. Omit any section whose source wasn't available. When email/docs/Slack connectors are absent, those sections are empty *by necessity* — note it once at the end (`Note: email/docs/Slack not connected`), don't imply the account is quiet everywhere. Quote blank fields as blank rather than inventing.

```
# Account Context: [Account Name]

## Current State
[2-3 sentences: where this account is, what's active, the headline]

## Salesforce
- **Owner:** [Name] · **Profile:** [Industry] | [Employees] | [Type][ | custom health/tier if present]
- **Open opps:** [N], $[total]
  - **[Opp Name]** — [Stage] $[Amount] closes [Date] | Next: [NextStep]
- **Recent closed:** [Won/Lost] [Name] $[Amount] ([Date])
- **Last activity:** [Date] — [Subject]

## Key Contacts
| Name | Title | Last Touch | Notes |
|---|---|---|---|

## Recent Correspondence (email)
- [Date] — [Subject] with [Names] — [one-line]

## Documents
- [Title] ([type], modified [Date])

## Internal Chatter (Slack)
- [#channel] [Date] — [one-line] [link]

## Gaps / Flags
- [e.g. "No activity in 30d on $XXk opp" · "NextStep blank" · "single-threaded — 1 contact"]

## Ask the Owner
[If the requester is NOT the owner — a suggested Slack DM to the owner. Conversational, lowercase opener, references the specific opp $ and one detail above, offers help. Hand drafting to `draft-outreach`.]

> hey — was looking at [Account], saw the $[X] opp at [stage]. [one specific detail]. anything you need from me on it?
```

Link the account and each opportunity inline (`https://[instanceUrl]/lightning/r/Account/[Id]/view`).

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), an account-brief visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
