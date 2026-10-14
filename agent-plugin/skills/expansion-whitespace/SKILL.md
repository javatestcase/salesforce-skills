---
name: expansion-whitespace
description: "Identify ranked expansion plays for one customer from Salesforce contacts, owned products and opportunities plus recent email, documents and Slack. Use to find evidence-backed whitespace, upsell paths or adjacent teams and products ready for outreach."
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

# Expansion Whitespace

Resolve account → ground → read → map whitespace → output. Product catalog is external knowledge — ask once. **Read-only:** this skill never writes to Salesforce; it surfaces ranked expansion plays as suggestions for the rep to pursue themselves.

## 1. Resolve the account

Shared/demo orgs collide on name. If user gave Salesforce Id, skip to Step 2. Otherwise:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 10) { edges { node { Id Name { value } Website { value } Type { value } Industry { value } Owner { Name { value } } } } } } } }\"}" })
```

**One match** → take its Id, continue to Step 2.

**Several** → STOP. Before Step 2, determine which account:
- **If user provided $amount or seat count:** Search Opportunities across ALL candidate account Ids to find which has the matching renewal/deal:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
    queryParams: { "q": "SELECT Id, AccountId, Account.Name, Name, Amount, CloseDate, StageName FROM Opportunity WHERE AccountId IN ('<ID1>','<ID2>',...) AND (Amount = <USER_AMOUNT> OR Name LIKE '%<USER_PRODUCT>%' OR CloseDate >= TODAY) ORDER BY CloseDate DESC LIMIT 50" })
  ```
  Match by Amount or product name. Take that AccountId, continue to Step 2.
- **Else:** List candidates (Name · Website/Industry · Owner · Id) and ask user to pick.

**None** → broaden name or ask for correct account. Don't guess.

## 2. Ground (hardcoded — Account + Contact)

Ground **Account + Contact** (both always exist). Lean projection discovers this org's custom fields without the full schema payload. **Fire as two separate calls** (combined ObjectInfo often overflows):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label } } } }\"}" })
```

From the results: note scalar `__c` fields (Success_Segment, License_Utilization, Job_Function, Job_Level, etc.) — take their `{ value }` in the read queries. Without `dataType`/`relationshipName`, you can't perfectly distinguish scalar vs reference fields, but most customs are scalar; reference fields that slip through will show Ids (cryptic but not broken). Standard relationships (`Account`, `Owner`, `Contacts`, `ChildAccounts`) are hardcoded in the queries below.

## 3. Read (fill from steps 1–2)

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields on Account; `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields on Contact (role, department, etc.).

**Fire TWO separate reads in ONE turn** (parallel, no dependency). Triple-nesting (Account > Opportunities > OpportunityLineItems) commonly fails; the split avoids errors.

**Read A — Account + Contacts + ChildAccounts:**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } <ACCOUNT_CUSTOM> Contacts(first: 30) { edges { node { Name { value } Title { value } <CONTACT_CUSTOM> } } } ChildAccounts { edges { node { Name { value } Industry { value } Owner { Name { value } } } } } } } } } } }\"}" })
```

**Read B — Won Opportunities + line items (the actual products/SKUs owned):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Account: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, IsWon: { eq: true } }, first: 30, orderBy: { CloseDate: { order: DESC } }) { edges { node { Name { value } Amount { value } CloseDate { value } StageName { value } Description { value } OpportunityLineItems(first: 50) { edges { node { Quantity { value } TotalPrice { value displayValue } Product2 { Name { value } } } } } } } } } } }\"}" })
```

The `OpportunityLineItems` child (span `Product2` for the SKU name, with `Quantity`/`TotalPrice`) is the real "Owned today" input for the Step 4 grid — one read, no extra round-trip (this is a single child level, not the triple-nesting that overflows). Fall back to `Opportunity.Name` only if the org doesn't use line items (empty `edges`).

For book-level sweep: replace Read A `where: { Id: { eq: ... } }` with `scope: MINE` or team filter, limit 20.

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

**Issue step 3 and all of step 3b as tool calls in a single turn.** They're independent (searches key on account name, not the SF result):
- **email**: threads mentioning teams/use-cases/products not yet sold, **plus recent events/invites/webinars as timing hooks**
- **docs**: recent transcripts/notes → teams/departments mentioned, **job changes, new projects**
- **slack**: internal mentions → expansion plays discussed

Use whatever email/doc/Slack search tools are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use. **Prioritize evidence from last 90 days for recency/relevance.**

## 4. Map whitespace

**Product catalog (external):** ask user for the product/SKU list once — never invent. Build owned-vs-possible grid:

| Dimension | Owned today | Whitespace | Evidence |
|---|---|---|---|
| Products / SKUs | [SKUs owned, from Read B's OpportunityLineItems (Product2 name · Quantity · TotalPrice); fall back to Opportunity.Name only if no line items] | [catalog items they haven't] | [need signal: mentioned in calls/emails? industry-typical?] |
| Teams / departments | [all contacts from Contacts child: name + title, not just technical subset] | [adjacent teams named in transcripts] | |
| Geography / subsidiaries | [entities under contract, plus reseller contacts if Account Type = reseller] | [child accounts with no spend] | |
| Volume / tier | [seats or usage from `__c`, penetration as exact % = seats/NumberOfEmployees] | [headroom vs employee count or benchmark, Success_Segment gap if present] | |

**Only call something whitespace if there is at least one piece of evidence** (stakeholder mentioned the team, transcript named the use case, org structure shows the entity). "They could theoretically buy everything" is not a finding.

## 4b. Cross-dimensional analysis (no extra reads — use data already fetched)

**Contact-to-product gap:** Cross-match contact titles/roles against owned products. Flag senior/exec/C-suite titles NOT reflected in product ownership (e.g., CIO with no BI tool seat, VP Sales with no CRM license = upsell hook).

**Child account routing:** For ChildAccounts with a different Owner than the parent, note the AE-to-AE warm intro path (e.g., "Parent CIO → intro to Child Account Owner [Name]").

## 5. Rank plays

**Prioritize by sales motion complexity, not just $ size:**
1. **Renewal add-ons** (bundle into active renewal — lowest friction)
2. **Warm intro expansions** (existing contact opens door — medium friction)
3. **Cold new products** (no prior relationship — highest friction)

When evidence strength is equal, prefer lower friction. Score on evidence strength, deal size potential, and access. **For reseller/partner accounts in "Owned today", name individual contacts, not just the entity.** Top plays get a one-line motion: who to approach, with what message, anchored on which existing success.

## 6. Output — expansion whitespace (primary, portable)

Assemble the plays as Markdown. This is the deliverable in any host. Cite the source per finding; quote blank fields as blank rather than inventing.

```
# Expansion Whitespace: [Account / scope]

## Owned vs possible
[the grid]

## Top plays
1. **[Play]** — est. $[range] — evidence: [source] — way in: [person/path] — first move: [action]
2. …

## Not yet credible (parking lot)
- [Items with no evidence — what signal would promote them]

## Suggested opportunities (for the rep to pursue)

For each top play, a suggested opportunity shape the rep can pursue themselves — presented as a suggestion only; this skill does not modify Salesforce:

📋 **[Account] — [Product/Play]**
- Name: "[Account] — [Product] Expansion"
- Account: [account name + link]
- Type: Existing Customer — Expansion
- Amount: $[estimated amount based on sizing heuristics]
- Stage: [initial stage, typically Discovery or Qualified]
- Close Date: [Q end date, 90–120 days out]
- Rationale: [evidence + way in + first move]

Repeat for each play.
```

Link the account inline (`https://[instanceUrl]/lightning/r/Account/[Id]/view`). For book-level sweeps, output a ranked account list with each account's single best play, plus the suggested opportunity shape for the rep to pursue.

## 7. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), an adoption-heatmap/expansion-plays visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 6 is the whole deliverable.
