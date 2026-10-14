---
name: customer-health
description: "Assess customer health from Salesforce account, renewal, case, task, and health data plus email, calendar, documents, and Slack. Use to judge risk, explain engagement or value trends, or prepare a business review; prospect meeting prep: call-prep."
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

# Customer Health

Two jobs, one data pass: the ongoing "are we okay here?" check, and the quarterly business review that proves value and sets up the next phase. Ground → (read + evidence, ONE turn) → score → output. **Read-only:** this skill never writes to Salesforce; it reads, scores, and links records, and hands any drafting to `draft-outreach`.

## Inputs

- **Account:** name or SFDC ID
- **Mode:** health check (default) or QBR prep
- **Period:** last quarter (default) for trend math

## 1. Ground (hardcoded — Account only)

Ground **only Account** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's health/adoption/renewal/NPS `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. Consider scalar `__c` fields worth using (health score, adoption/seat usage, renewal date, ARR, NPS, tier) — ground them once and reuse. Standard fields, the `Owner`/`Opportunities`/`Cases` spans, and `LastActivityDate` are reliable across orgs; an org that doesn't use Cases just returns empty `edges`, not an error. Do not output all the field names.

## 2. Read (fill from step 1)

`%ACCOUNT%` = the user's match (1–2 words); swap for `Id: { eq: "..." }` when an SFDC Id was given instead of a name. One call pulls the account plus its open-renewal-relevant opportunities and recent cases — no separate read per object.

**Field rule (avoids the retry loop):** add grounded custom fields only as `Field__c { value }` (`{ value displayValue }` for currency/picklist). Use the standard `Owner` span already written in the template; never invent a relationship span from a raw `Id`/`__c` field. Insert `<ACCT_CUSTOM>` = confirmed Account `__c { value }` fields.

Treat this GraphQL read template as literal. Replace only `%ACCOUNT%`, `<ACCT_CUSTOM>`, or the documented exact-Id filter. Do not reconstruct, shorten, flatten, or remove its trailing closing delimiters.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 1) { edges { node { Id Name { value } Type { value } Industry { value } AnnualRevenue { value displayValue } LastActivityDate { value } CreatedDate { value } <ACCT_CUSTOM> Owner { Name { value } } Opportunities(first: 20, orderBy: { CloseDate: { order: DESC } }) { edges { node { Id Name { value } Type { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsWon { value } } } } Cases(first: 10, where: { CreatedDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { CreatedDate: { order: DESC } }) { edges { node { CaseNumber { value } Subject { value } Status { value } Priority { value } CreatedDate { value } } } } Tasks(first: 20, where: { ActivityDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } } } } } } } } } }\"}" })
```

Empty `edges` on `Account` → broaden `%ACCOUNT%`, or ask the user for the right account. Empty `edges` on `Cases`/`Tasks` just means none in the window — don't retry, don't treat as an error. The `Tasks` child (last 90d) is the in-CRM activity cadence behind the Engagement-trend dimension — read it even when no external calendar/email connector is present.

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b in a single turn — don't wait for the SF read to return before firing the searches.** They're independent (searches key on the account name from the request, not the SF result), so batch them together:
- **email**: threads with this account's contacts, last ~90d → cadence vs prior period, most recent exchange + topic
- **calendar**: meeting count/attendees last ~90d vs prior period — is the champion/exec still showing up
- **docs**: success plan, past QBR decks, recent notes → documented outcomes, open commitments
- **slack**: internal mentions → deal-desk/exec concerns, escalations

Use whatever email/calendar/doc/Slack tools are available; skip silently if none are present (SFDC-only is fine). Be explicit about what this skill can't see: product usage, support-ticket detail, and NPS only count if synced into a CRM field or a connected doc — otherwise mark that dimension "not visible from CRM" rather than guessing. Cite source + date for anything you use.

## 3. Score the health (cite every value; invent nothing)

| Dimension | Signal | Status |
|---|---|---|
| Relationship | champion/exec engagement (evidence), breadth of contacts active | 🟢🟡🔴 |
| Engagement trend | in-CRM `Tasks` cadence (step 2, last 90d) + meeting/email cadence (evidence) vs prior period | |
| Commercial | renewal proximity (open renewal opp `CloseDate`), open expansion, payment/contract issues | |
| Support | open Cases, aging/priority from step 2 | |
| Value delivery | documented outcomes vs the success plan (docs), if one exists | |

Overall verdict with the one or two dimensions driving it.

## 4. Output — health read (primary, portable)

Assemble the health read as Markdown. This is the deliverable in any host. Cite every value; omit any dimension whose source wasn't available (mark it "not visible from CRM").

**Health check mode:**
```
# Health: <Account> — 🟢/🟡/🔴
<verdict sentence>
<dimension table with evidence>

## Watch items
- <specific signal, why it matters, suggested action>

## Suggested CRM edits (for the rep to make)
- <health/status fields, if grounded> — these live on the Account record; show before/after as a checklist. This skill reads only; make the edits in Salesforce yourself or hand them to a guided-write skill.
```

**QBR prep mode:** add the meeting kit —
1. **Value delivered** — outcomes since last review, in their metrics, with sources
2. **Adoption story** — what's working, what's underused (only CRM/document-visible facts)
3. **Open items** — Cases resolved/open, commitments from last QBR and their status
4. **Next phase** — the expansion plays (`expansion-whitespace`) and renewal framing (`renewal-radar`) worth raising
5. **Agenda + attendees** — who should be in the room from the stakeholder map, and the asks for their execs

Link the account inline (`https://[instanceUrl]/lightning/r/Account/[Id]/view`). Lead with the single most important health read as a one-line callout above the sections.

## 5. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a composite-health meter, engagement trend chart, and health-signals datagrid may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 4 is the whole deliverable.
