---
name: salesforce-hygiene-check
description: "Audit open Salesforce opportunities for missing fields, stale dates, weak next steps, stage mismatches and single-threading, producing prioritized fixes. Use to check pipeline data quality, find incomplete deals or plan CRM cleanup without changing records."
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
> only** (via Headless 360 `dispatch_readonly`). This skill audits open opportunities and
> outputs a prioritized recommendations checklist; it never writes to Salesforce. The rep
> applies each recommendation themselves in the CRM. On a host whose Salesforce connector has
> a different read tool (for example, Amazon Quick), send the same `url` and query through
> that tool.
<!-- /global-rules-bootstrap -->

# Salesforce Hygiene Check

Read-only audit of open opps → a fix checklist the rep applies themselves (nothing is written). Ground → one read → run checks → output. **Read-only:** never writes to Salesforce; the output is recommendations only.

## 1. Ground (hardcoded — Opportunity only)

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's `__c` hygiene fields (competitor, required-per-stage, next-step trackers) — use exact names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

## 2. Read the open book (one call, scope: MINE)

`scope: MINE` = running user's book (no user lookup). Splice confirmed `__c` fields into `<OPP_CUSTOM>`. **Check `{` vs `}` balance before issuing** — splicing custom fields is where a brace drops.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 200) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } CreatedDate { value } Type { value } LeadSource { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Role { value } Contact { Name { value } } } } } } } } } } }\"}" })
```

`InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry.

## 3. Run checks (per opp)

Flag: **Amount** blank/$0 · **CloseDate** past, or unchanged since creation on a >30d opp · **NextStep** blank or unchanged 14d+ · **Stage age** stuck (>2× median) · **Activity** LastActivityDate >14d · **Contacts** none or single-threaded (≤1 role) · **Stage criteria** exit criteria not evidenced. Required-per-stage expectations are external — infer from the org's data or ask once; never invent.

## 4. Suggest values (cite real names — never generic "champion")

Per flag, propose a value the rep can enter themselves: **NextStep** `MM/DD - <verb> <what> with <real Contact name>` from recent email/doc context · **CloseDate** realistic per stage + median cycle · **Stage** correct stage if evidence shows a mismatch. These are suggestions only — the rep enters them in the CRM.

## 5. Output — hygiene recommendations checklist (primary, portable)

Validate bucket counts: critical + attention + clean = total open.

```
# Salesforce Hygiene Check — <N> open opps
## Summary
- 🔴 Critical (<N>): past close dates, $0 amounts
- 🟡 Attention (<N>): stale NextStep, no activity 14d+, single-threaded
- ✅ Clean (<N>)
**Validation:** <crit> + <attn> + <clean> = <N total>
## Fix List
### <Account> — <Opp>  [link]  ·  Stage <X> | $<Amt> | Close <Date>
- ⚠️ <issue> …
> **Suggested NextStep:** `MM/DD - <verb> <what> with <Contact>`
> **Suggested CloseDate:** `<Date>` (current is past)
---
## Bulk recommendations
- <N> opps need CloseDate refreshed · <N> opps have no Contact Roles
```

Recommendations only — the rep applies each one themselves in Salesforce (this skill writes nothing). Link each opportunity inline.

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a hygiene-state donut, issue-frequency chart, and a flagged-opps datagrid may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see `com.salesforce.quick/ui`. When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
