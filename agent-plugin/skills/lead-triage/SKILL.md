---
name: lead-triage
description: "Produce an inbound-lead priority and routing recommendation from Salesforce Lead and Account data, research and email engagement. Use when qualifying a new lead, assessing ICP fit and intent, choosing an owner or deciding the response speed and next step."
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
> **Portability note.** Written for the Agent Plugins standard. Salesforce access is **read-
> only** (via Headless 360 `dispatch_readonly`). This skill scores and routes a lead; it never
> writes to Salesforce and never sends email — any outreach is handed to `draft-outreach`. On
> a host whose Salesforce connector has a different read tool (for example, Amazon Quick),
> send the same `url` and query through that tool.
<!-- /global-rules-bootstrap -->

# Lead Triage

Ground → read Lead + Account → enrich → score → route. **Read-only:** no per-lead follow-ups written, no Salesforce writes — the reads have the data.

## 1. Ground (hardcoded — Lead and Account)

Ground **Lead** and **Account** (for ICP fields). Both always exist. Issue these independent requests in the **same tool turn** so they run in **parallel**:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Lead\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

From each response, select relevant `__c` fields by API name and label (segment, industry, employee count, lead score, MQL status, etc.) and take their `{ value }`. The `Owner` spans below are standard and hardcoded. A Lead can be owned by a user or a queue, so the Lead read selects the owner's name through `... on User` / `... on Group` fragments; a plain `Owner { Name }` on Lead fails with `FieldUndefined`. If a grounding response is very large and truncates, filter to the `__c` fields whose labels match your keywords; if you can't load it, proceed with standard fields only — don't keep retrying.

## 2. Read lead + matching account (templated, one turn)

Fire these as tool calls in **one turn** (independent). Insert `<LEAD_CUSTOM>` = confirmed scalar `__c` fields on Lead, `<ACCOUNT_CUSTOM>` = confirmed scalar `__c` fields on Account.

**Lead (by identifier user provided — Id, email, or name+company):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Lead(where: { <LEAD_FILTER> }, first: 1) { edges { node { Id Name { value } Company { value } Title { value } Email { value } LeadSource { value } Status { value } CreatedDate { value } <LEAD_CUSTOM> Owner { ... on User { Name { value } } ... on Group { Name { value } } } } } } } } }\"}" })
```

**Account (by company name or domain):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { or: [{ Name: { like: \\\"%<COMPANY>%\\\" } }, { Website: { like: \\\"%<DOMAIN>%\\\" } }] }, first: 5) { edges { node { Id Name { value } Type { value } <ACCOUNT_CUSTOM> Owner { Name { value } } } } } } } }\"}" })
```

`<LEAD_FILTER>` = build from user input: `Id: { eq: "<id>" }` OR `Email: { eq: "<email>" }` OR `and: [{ Name: { like: "%<name>%" } }, { Company: { like: "%<company>%" } }]`

If Account exists with Owner → existing relationship, routing = coordinate with that owner.

**Web research (parallel with SF reads):** Use web search/fetch if available to find company size, industry, funding, recent news. Fire in SAME turn as SF reads. If tools absent, skip silently.

**Email search (parallel):** Use email search if available to find prior threads from this domain. Fire in SAME turn. If tool absent, skip silently.

## 3. Score ICP fit

Against ICP (ask the user once if not inferrable from org data):

| Dimension | Fit | Evidence |
|---|---|---|
| Industry | ✅ / ⚠️ / ❌ | [from Account/web] |
| Size | ✅ / ⚠️ / ❌ | [from Account custom/web] |
| Persona (title) | ✅ / ⚠️ / ❌ | [from Lead.Title] |
| Disqualifiers | ✅ none / ❌ [which] | [check against ICP] |

## 4. Score intent

| Signal | Strength |
|---|---|
| Source quality | High (demo request, referral) / Med (content, event) / Low (list, cold) |
| Message specificity | Specific use case / Generic interest / None |
| Prior engagement | Email thread / SFDC history / None |
| Timing trigger | Recent funding, hiring, exec change / None |

## 5. Assign priority

Calibration: P0 ≈ top 20%, P1 ≈ next 25%, P2 ≈ remaining.

- **P0:** Strong ICP fit AND high intent (specific ask, demo request, or hot trigger)
- **P1:** Strong fit with medium intent, OR moderate fit with high intent
- **P2:** Moderate fit with low intent, or fit unclear
- **DQ:** Hard disqualifier hit

Override: if the Account exists with an owner → routing = "coordinate with [owner]".

## 6. Output — triage recommendation (primary, portable)

```
# Lead Triage: [Lead Name] — [Company]

**Priority:** [P0 / P1 / P2 / DQ]
**Route to:** [owner / SDR / coordinate with existing owner]
**Respond by:** [speed recommendation]

## ICP fit
[the fit table]

## Intent
[the intent table]

## Recommended next step
- [the one action — e.g. "Book discovery this week"; hand drafting to draft-outreach]
```

Link the Lead and any matched Account inline. Do not draft outreach here — recommend it and hand off to `draft-outreach`.

## 7. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a tier/score view may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see `com.salesforce.quick/ui`. When no rich surface is available, the Markdown in Step 6 is the whole deliverable.
