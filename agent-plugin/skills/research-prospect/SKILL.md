---
name: research-prospect
description: "Build a prospect brief from web research and Salesforce, covering company facts, recent signals, likely priorities, contacts and ICP fit. Use to research a net-new company or person before outreach. Existing accounts: account-context."
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
> read-only. It also uses the host's web-research tool. On a host whose Salesforce connector
> has a different read tool (for example, Amazon Quick), send the same `url` and query through
> that tool.
<!-- /global-rules-bootstrap -->

# Research Prospect

Ground Account → CRM duplicate-check + web research (ONE turn) → score fit → output. This skill targets companies NOT yet in your CRM, so the work is mostly web research; the Salesforce read is a duplicate-check so you don't step on a colleague's account. **Read-only:** this skill never writes to Salesforce; it produces a brief and a suggested next step.

## 1. Inputs

- **Company name or domain** (required)
- **Contact name or title** (optional)

ICP (industries, size, titles, disqualifiers), value prop, competitors, differentiators are external knowledge — infer from org data or confirm with the user once. Never invent.

## 2. Ground Account (this turn), then CRM duplicate-check + web research (ONE turn)

**Ground Account first** — its `__c` fields are this org's ICP schema (tier, segment, territory, employee band, etc.), and Step 3 scores fit against them. Account always exists, so this one call never fails on a missing object:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })
```
From the result, note the scalar `__c` fields whose label carries ICP/segment/tier/territory/employee-band signal — add each as `Field__c { value }` to `<ACCOUNT_CUSTOM>` in the read below. Just scan the result by eye. If grounding is unwieldy, skip it and use the standard fields below only — don't retry.

**CRM duplicate-check + web search — fire BOTH as tool calls in ONE turn (independent).**

**Salesforce** — check whether the company is already an Account over GraphQL (Account is UI-API-serviceable). Insert `<ACCOUNT_CUSTOM>` = the confirmed scalar `__c { value }` fields from grounding.

Match on **`Name` first**. Do **not** combine Name and Website with `or` — a two-clause `or` in a UI-API `where` 500s on this endpoint. Only if the name search returns no rows, run the Website-only fallback below.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 5) { edges { node { Id Name { value } Website { value } Industry { value displayValue } NumberOfEmployees { value } Type { value displayValue } <ACCOUNT_CUSTOM> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```
- **Found** → note owner, open opps, known contacts. Output must say "already in CRM, owned by [Name]" prominently so the user doesn't step on a colleague.
- **No rows** → run the **Website-only fallback** (a `%DOMAIN%` match), still no `or`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Website: { like: \\\"%DOMAIN%\\\" } }, first: 5) { edges { node { Id Name { value } Website { value } Industry { value displayValue } NumberOfEmployees { value } Type { value displayValue } <ACCOUNT_CUSTOM> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```
- **Still no match** → "net new — no CRM record". Broaden `%…%` once if a partial name seems likely; don't retry the same shape.

**Web search** (same turn, independent of the SFDC result):
- Company basics: what they do, HQ, size, funding stage, leadership.
- Recent signals (last 6 months): funding rounds, exec hires, product launches, layoffs, earnings, expansion.
- Tech/operating context relevant to your product category.
- Likely priorities, inferred from the signals (e.g. just raised → hiring + scaling; new CRO → pipeline overhaul).
- If a contact was specified: their role, tenure, prior companies, public talks/posts, and what they likely care about.

## 3. ICP fit scoring

| Dimension | Fit | Evidence |
|---|---|---|
| Industry | ✅ / ⚠️ / ❌ | [from research] |
| Company size | ✅ / ⚠️ / ❌ | [employee count vs ICP range] |
| Buyer persona present | ✅ / ⚠️ / ❌ | [title found / inferred] |
| Disqualifiers | ✅ none / ❌ [which] | |
| Timing signal | ✅ / ⚠️ / ❌ | [recent trigger event or none] |

Overall: **Strong fit / Moderate fit / Poor fit** with one-sentence rationale.

## 4. Relevance hooks

2–3 specific, sourced hooks for outreach — things from the research that connect to your value prop. Not generic ("they're growing") but specific ("they posted 12 [relevant role] openings last month and their [exec title] spoke about [relevant pain] at [conf]").

## 5. Output — prospect brief (primary, portable)

Assemble the brief as Markdown. This is the deliverable in any host. Quote blank fields as blank rather than inventing; cite the source per signal.

```
# Prospect Research: [Company]

## CRM Status
[Already in Salesforce — owned by [Name], [N] open opps | OR | Net new — no CRM record]

## Company Snapshot
- What they do: [one line]
- Size / stage: [employees, funding]
- HQ: [location]
- Leadership: [key names + titles]

## Recent Signals
- [Date] — [Signal] ([source])
…

## [Contact Name] (if specified)
- Role / tenure / background
- What they likely care about

## ICP Fit: [Strong / Moderate / Poor]
[Scoring table]
[One-sentence rationale]

## Relevance Hooks
1. [Specific hook] — ties to [your value prop angle]
2. …

## Suggested Next Step
[e.g. "Run draft-outreach targeting [Contact]" or "Low fit — log as disqualified" or "Already owned by [Name] — coordinate before reaching out"]
```

When the company is already in CRM, link the Account inline (`https://[instanceUrl]/lightning/r/Account/[Id]/view`).

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a prospect-brief/ICP-fit visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
