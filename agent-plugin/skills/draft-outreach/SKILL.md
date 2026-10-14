---
name: draft-outreach
description: "Create a personalized email draft from Salesforce contact, account, opportunity and activity data plus prior email, documents and Slack. Use when starting, following up with or re-engaging one prospect or customer. For batch inbox replies, use inbox-sweep."
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
> here is **read-only** (via Headless 360 `dispatch_readonly`). The only write this skill
> performs is creating an **email draft** through the host's email connector — it **never
> sends**. This "draft, then let the human review and send" discipline is the skill's core
> safety contract and must be preserved on every host: no auto-send, no Salesforce record
> writes. On a host whose Salesforce connector has a different read tool (for example, Amazon
> Quick), send the same `url` and query through that tool.
<!-- /global-rules-bootstrap -->

# Draft Outreach

Ground → (read + evidence searches, all in ONE turn) → draft → **create draft (never send)** → present for review.

Value prop, proof points, voice/tone, signature block, and competitors (to avoid naming unprompted) are external knowledge — infer from the org's own closed-won data and product catalog, or ask the user once. Never invent them.

## 1. Ground (hardcoded — Contact only)

Ground **only Contact** — it always exists (naming a missing custom object fails the whole call). Its fields + child relationships reveal this org's persona/segment schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label relationshipName } childRelationships { childObjectApiName relationshipName } } } }\"}" })
```

Step 1 is the authority on names. Note: (a) scalar `__c` fields (persona, segment, relationship-context) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's name; (c) each child `relationshipName` beyond the two standard ones below.

## 2. Read (fill from step 1)

`%NAME%` = recipient's name and `%COMPANY%` = the company/account named in the request (swap `Name: { like: … }` for `Email: { eq: \"%EMAIL%\" }` when given an email). **Reference-field rules (avoids the retry loop):**
- A scalar/`__c` field → `Field__c { value }` (`displayValue` is null for Id fields here).
- For a **related record's name**, span via the exact `relationshipName` from Step 1. Do NOT append `{ … }` to a raw `Id`/`__c` field.
- Only span relationships Step 1 returned. No usable relationshipName → take the `__c { value }` (the Id) and move on — do not retry.

Insert `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed org-specific relationship. `Account` (parent) and `OpportunityContactRoles` (child) always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { Name: { like: \\\"%NAME%\\\" } }, first: 1) { edges { node { Id Name { value } Title { value } Email { value } LastActivityDate { value } <CONTACT_CUSTOM> Account { Name { value } Industry { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Opportunity { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } } } } } Tasks(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } TaskSubtype { value } } } } Events(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } Opportunities(where: { IsClosed: { eq: false } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } } } } }\"}" })
```

Empty `edges` → broaden `%NAME%`. **Prior-contact detection reads BOTH children plus the email search** — `Tasks` carries logged emails, `Events` carries calls/meetings; take the most-recent touch across Tasks, Events, AND the 2b email threads. `Task.TaskSubtype` labels the last touch email-vs-call. If a read errors on `Events` (`FieldUndefined`/`InvalidSyntax`), re-issue **without** the `Events` block (Tasks-only) rather than failing the whole read; don't retry byte-identical.

Given a **company only** (no person named): skip Step 1 grounding and read the Account with standard fields only (its `Tasks`/`Events` children fill the "Prior contact" line):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } } } } Tasks(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } TaskSubtype { value } } } } Events(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } } } }\"}" })
```

## 2b. Evidence (run IN PARALLEL with step 2 — same turn)

They key on the recipient/company name from the request, not the SF result, so batch them with step 2:
- **email**: prior threads with this recipient — last exchange date + topic (warm follow-up vs. cold).
- **docs**: recent notes/transcripts mentioning the account — hooks, decisions, objections.
- **slack**: internal mentions of the account/contact — context worth referencing.

Use whatever email/doc/Slack connectors are available; skip silently if none (SFDC-only is fine). Cite source + date for anything you use.

## 3. Draft the email (cite every claim; invent nothing)

If step 2 AND 2b both come back empty (no SFDC record, no prior threads): run a lightweight pass — company basics + one recent signal — before drafting; never draft on invented context.

Structure (body under 120 words):
1. **Relevance line** — one sentence proving you did homework, sourced from step 2/2b. Never "I came across your company."
2. **Value bridge** — connect their situation to the value prop; use a proof point if it fits naturally.
3. **Soft ask** — one low-friction CTA. Default: "Worth a 20-min call to see if this maps to what you're working on?"
4. **Signature** — the block the user provided, or sampled from sent mail.

Tone: match the team voice (sampled from sent mail, or as directed); concise and direct — no "hope this finds you well," no paragraph intros. Subject: 4–7 words, specific not salesy — references the hook, not the product.

## 4. Create the email draft — DRAFT ONLY, NEVER SEND

Use the email connector to **create a draft** (To = recipient email, Subject = generated, Body = generated). **Do not send.** Capture the draft's ID/link to include in the output. If the email connector can only send (not draft), do **not** send — instead return the subject and body as text for the user to paste, and say a draft could not be created. Sending is always the user's action, never yours.

## 5. Output — draft summary (primary, portable)

Present the created draft for review. This is the deliverable in any host.

```
# Outreach Draft → [Recipient Name], [Title] @ [Company]

**Intent:** [COLD INTRO / WARM FOLLOW-UP / RE-ENGAGE / REFERRAL / EVENT FOLLOW-UP]

**Context used:**
- CRM: [summary of SFDC findings or "net new"]
- Prior contact: [last thread date + topic, or "none — cold"]
- Hook: [the relevance angle used]

---
**Subject:** [subject line]

[email body]
---

✉️ Created as an email draft (not sent): [link/ID]
Review, edit, and send it yourself from your drafts folder.

**Suggested SFDC logging** (do manually, or via a write-capable connector — this skill does not write to Salesforce):
- Log Activity on [Account/Contact]: "Outbound email — [subject]"
```

Every context line must trace to a real Step 2/2b finding — drop lines you lack data for rather than pad.

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a draft-review card (context signals + the verbatim draft + a "revise" action) may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). Any "revise" action must re-draft, never send. When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
