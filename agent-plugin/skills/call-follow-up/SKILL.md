---
name: call-follow-up
description: "Create a customer follow-up email and internal recap from a meeting transcript plus Salesforce account and opportunity history. Use after a customer call to capture decisions, commitments, objections, open questions, next steps, and proposed CRM updates."
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
> **Portability & write posture.** Written for the Agent Plugins standard. Salesforce access
> here is **read-only** (via Headless 360 `dispatch_readonly`). The skill's outputs are an
> email **draft** and a Slack **draft** created through the host's email/Slack connectors — it
> **never sends** either. Any Salesforce updates are presented as a **checklist for the user
> to apply**; this skill does not write to Salesforce. No auto-send, no unattended record
> writes. On a host whose Salesforce connector has a different read tool (for example, Amazon
> Quick), send the same `url` and query through that tool.
<!-- /global-rules-bootstrap -->

# Rules

- Gather thorough, contextual background before acting. Explain material errors and inference logic explicitly in the final output.

# Call Follow-Up

Get transcript → extract structure deeply → (draft email + draft Slack + SFDC read with historical context, all ONE turn) → output. **Draft-only:** email and Slack are created as drafts and never sent; SFDC changes are a checklist, not writes.

**Voice/tone, email signature, and team Slack channel are external knowledge** — infer from org data or ask once. Never invent.

## 1. Get transcript

**If link or "find it":** use doc-search tools (Google Workspace, etc.) to read the doc. Search by account name if needed. **If pasted:** use as-is.

Extract: attendees (internal + external), date, account name.

## 2. Extract structure (analyze transcript deeply)

From transcript, pull: **Decisions** (agreed/confirmed), **Customer commitments**, **Our commitments**, **Open questions**, **Objections/concerns**, **Next meeting** (if scheduled), **Qual signals** (budget/authority/timeline/pain — BANT/MEDDIC default or infer), **Specific human moments** (quotes/phrases for personalization), and **Urgency signals** (timeline drivers, forcing events).

## 3. Read context, then draft email + Slack

**A. Draft customer email** (under 150 words) — thank-you opener referencing a specific human moment from the call; recap agreed next steps (their commitments + ours) as short bullets; answers/links you committed to (use `[ATTACH: description]` if not yet available); propose/confirm the next meeting; minimal signature. Tone: warm, specific, or matched to org voice. **Create as an email draft to external attendees. Do not send.**

**B. Draft Slack summary** for the team channel (ask which if unspecified):
```
*[Account] - [Call type] - [Date]*
Stage: [Opp stage] $[Amount]
Attendees: [names]

*TL;DR:* [one sentence on where the deal is]

*Key points:*
• [decision/signal]

*Risks / objections:*
• [concern raised]
• [flag urgency gaps if no forcing event surfaced]

*Next steps:*
• [ ] Us: [commitment] - [owner] by [date]
• [ ] Them: [commitment]

*SFDC updates needed:* [stage change / next step / amount]
```
Post as a **draft** message (or output for the user to copy if a Slack draft isn't available). Do not post to a channel without the user's action.

**C. Read SFDC context** (fill the Slack summary, check for existing account/opps, propose updates). Ground Account and Opportunity in the same tool turn:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```
Then read account + all opps (open + historical) with two reads in the same turn, both filtered by account name (`%NAME%`):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%NAME%\\\" } }, first: 1) { edges { node { Id Name { value } <ACCOUNT_CUSTOM> Owner { Name { value } } } } } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Account: { Name: { like: \\\"%NAME%\\\" } } }, first: 50, orderBy: { CloseDate: { order: DESC } }) { edges { node { Id Name { value } AccountId { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } IsWon { value } NextStep { value } <OPP_CUSTOM> } } } } } }\"}" })
```
Insert `<ACCOUNT_CUSTOM>`/`<OPP_CUSTOM>` = confirmed `__c { value }` fields whose labels match the follow-up context. If the name filter matches multiple accounts, keep only opps whose `AccountId` matches the resolved Account `Id`. **Historical context matters:** if no active opp, note closed/dead opps exist (account is known — prevents duplicate creation, surfaces prior relationship). Empty account match → broaden `%…%` or note the account isn't in CRM yet. On a system error (500/timeout/auth), log it in the output and explain what you inferred and why.

## 4. SFDC update checklist (proposed — not written)

Propose changes based on the call; the user applies them. This skill does **not** write to Salesforce.
- If an **account exists** (from Step 3C), note the AccountId — don't propose a duplicate.
- If **no account found**, propose Account creation with fields from the transcript (for the user to create).
- If **old closed/dead opps exist**, surface that prior-relationship context.
- Proposed: `NextStep` → suggested; `StageName` → if progression warranted; `Amount` → if discussed; `CloseDate` → if timeline shifted; **Log Activity** → "[Call type] - [one-line summary]".

## 5. Output — follow-up package (primary, portable)

```
# Call Follow-Up: [Account] - [Date]

## Customer Email  (draft — not sent)
✉️ Drafted to [recipients]: [draft link]
---
[email body preview]
---

## Internal Summary  (draft — not posted)
💬 Drafted to [#channel]
---
[slack message preview]
---

## Update Salesforce  (checklist for you to apply — this skill does not write)
- [ ] NextStep: "[value]"
- [ ] [other fields]
- [ ] Log Activity

## Our Commitments (don't drop these)
- [ ] [commitment] - by [date]
```

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a follow-up card may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see `com.salesforce.quick/ui`. Any action button must draft/propose, never send or write. When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
