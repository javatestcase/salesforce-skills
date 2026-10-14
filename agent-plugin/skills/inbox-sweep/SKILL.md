---
name: inbox-sweep
description: "Create a prioritized response queue and email drafts from unread threads, sent-mail voice patterns and Salesforce account and opportunity context. Use when sweeping or triaging an inbox, finding messages needing replies or drafting several customer responses."
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
> is **read-only** (via Headless 360 `dispatch_readonly`). Replies are created as email
> **drafts** through the host's email connector — the skill **never sends** them. SFDC logging
> is a handoff/suggestion, never an inline write. No auto-send, no Salesforce writes. On a
> host whose Salesforce connector has a different read tool (for example, Amazon Quick), send
> the same `url` and query through that tool.
<!-- /global-rules-bootstrap -->

# Inbox Sweep

Unread customer emails → classify, prioritize, draft replies (as email drafts). Cap 25 emails / 10 drafts per sweep. Lookback: 72h default. **Draft-only:** every reply is a draft; nothing is sent.

## 1. Voice + candidate emails (one turn)

Read ~30–40 recent **external** sent emails to build an implicit style profile (greeting, length, sign-off, formality) — don't show it, just match it. In the same turn, search the inbox: **unread, last <lookback>, not from your internal domain**.

## 2. Match senders to Accounts

Collect the candidate sender domains, then ONE Account read matching them (drop `scope: MINE` for a broader sweep).

**Note:** When using `scope: MINE`, do not query `currentUser` for scoping; the scope already identifies the running user's records. Follow the global connectivity rule before reporting the connector unavailable.

**Note:** Salesforce record `Id` is a scalar. When an ID is needed, select it as bare `Id`; never use the invalid `Id { value }` form.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(scope: MINE, first: 200) { edges { node { Name { value } Website { value } Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, first: 5, orderBy: { CloseDate: { order: ASC } }) { edges { node { Name { value } Amount { value displayValue } StageName { value displayValue } CloseDate { value } NextStep { value } } } } } } } } }}\"}" })
```

Match only by normalized sender domain and a returned Account's `Website`. Do not infer a match from Account or Opportunity names; when no exact domain match is returned, do not attach an Account, Opportunity, amount, or stage to that email. The open `Opportunities` child (same read) grounds Step 4 prioritization (Amount, soonest CloseDate) and fills the output **Opp** column (`$<Amount> · <StageName label>`) — no per-account follow-up read.

## 3. Classify each (read the full thread, not just the latest)

- **Needs reply — deal**: question/request/decision on an active opp → draft
- **Needs reply — scheduling**: proposing/confirming a time → draft availability
- **Needs reply — support**: product/technical → draft ack + flag support handoff
- **FYI only**: CC/newsletter/auto → archive
- **Intro / new inbound**: first contact → route to `lead-triage`
- **Couldn't draft**: needs info only the user has → surface the blocking question
- **Sensitive — skip**: personnel/legal/exec → flag, don't draft

## 4. Prioritize (within needs-reply)

Open opp closing ≤30d > explicit deadline/urgency > larger Amount > older unread.

## 5. Draft replies (priority order, cap 10) — DRAFT ONLY, NEVER SEND

Full thread context; match the voice profile; answer the ask directly + confirm next step; <120 words; **create in-thread as a draft (reply), never send**. Scheduling → propose 2–3 calendar slots. Support → brief ack + "looping in <support>". SFDC logging stays a `log-activity` handoff (never write inline). If the email connector can only send (not draft), do **not** send — return the reply text for the user to paste.

## 6. Output — reply queue (primary, portable)

```
# Inbox Sweep — <N> customer emails (<lookback>)

## Drafted Replies (<N>)  (drafts — not sent)
| Pri | From | Account | Subject | Opp | Draft |
| --- | ---- | ------- | ------- | --- | ----- |

## FYI Only (<N>) — safe to archive
## New Inbound (<N>) — run lead-triage
## Couldn't Draft — need your input (<N>)  · <blocking question>
## Sensitive — skipped (<N>)  · <why>
## Flagged for Support (<N>)

## Suggested SFDC logging (do manually, or via a write-capable connector — this skill does not write)
- <Account>: Log Activity "Inbound email — <subject>"
```

All replies are drafts — review and send them yourself from email.

## 7. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a prioritized reply-queue view may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see `com.salesforce.quick/ui`. Any action button must draft, never send. When no rich surface is available, the Markdown in Step 6 is the whole deliverable.
