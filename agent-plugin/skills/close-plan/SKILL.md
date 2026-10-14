---
name: close-plan
description: "Build a customer-facing business case and dated mutual action plan from Salesforce opportunity data plus transcripts, email, documents, and Slack. Use to frame why buy and why now, quantify return, map the path to signature, or test the close date."
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

# Close Plan

Ground → read opp → gather evidence (all ONE turn) → draft business case + MAP. **Read-only:** this skill reads Salesforce and produces documents for the rep; it never writes to Salesforce, and hands any outreach drafting to `draft-outreach`/`call-follow-up`.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists. Its fields reveal this org's real custom and lookup schema; don't assume object names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

From the result: (a) scalar `__c` fields (business-case data, why-now, ROI, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's Name. The standard contact-role child is hardcoded below.

## 2. Read opp + evidence (issue ALL in one turn)

`%DEALNAME%` = 1–2 words. Reference-field rules: scalar → `Field__c { value }`; related name → span via the exact `relationshipName`: `<relationshipName> { Name { value } }`. Only span relationships Step 1 returned. If no usable relationshipName, take the `__c { value }` (the Id) and move on.

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed custom lookup relationship. Standard fields + `OpportunityContactRoles` always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } Description { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } } } } } } }\"}" })
```

Empty `edges` → broaden `%…%`.

**Evidence (in PARALLEL with step 2 — same turn):** Fire email/doc/Slack searches keyed on the deal/account name; these don't depend on the SF result. Use whatever tools are present; if none, skip silently.

- **Call transcripts / proposals:** customer's stated problems, success metrics, quantified pain, who said what.
- **Email:** commitments already made in writing, procurement/legal/security threads.
- **Slack:** internal deal-desk/exec mentions, concerns.
- **deal-advance-gap output** (if run this session): its known gaps feed the mutual action plan directly — don't re-derive them.

## 3. Draft business case

**Value prop, differentiators, required stakeholders for close, and internal approval chain are external knowledge — infer from the org's own data or ask the user once. Never invent it.**

In the customer's language, grounded in their own words (cite the call/email each point comes from):

1. **Current state and cost of it** - the problem as they described it, quantified where they gave numbers
2. **Desired outcome** - their success metrics, their timeline drivers (the why-now)
3. **Proposed solution** - what they're buying, mapped to each outcome
4. **Investment and return** - price vs. the quantified value; keep the math simple and attributable
5. **Risk of waiting** - what the delay costs in their terms
6. **Why us** - only differentiators they have actually reacted to

Flag every claim that has no customer evidence behind it — those are the points to validate on the next call, not assert in the doc.

## 4. Draft mutual action plan

Work backward from the target signature date (default: opportunity CloseDate) through both sides' steps: remaining validation, security review, legal redlines, procurement, signatures, plus any internal approvals the user mentions. Each row: step, owner (us / customer / named person), target date, status. Flag the steps whose dates make the CloseDate impossible.

## 5. Output — business case + MAP (primary, portable)

Assemble the business case and mutual action plan as Markdown. This is the deliverable in any host. Blank fields stay blank; drop steps with no data; never invent content.

```
# Close Plan: [Opp Name] - [Account]

## Business Case (customer-facing doc)

### Current State
[Problem as they described it, quantified where they gave numbers]

### Desired Outcome
[Their success metrics, their timeline drivers]

### Proposed Solution
[What they're buying, mapped to each outcome]

### Investment and Return
[Price vs. quantified value — simple math, attributable]

### Risk of Waiting
[What the delay costs in their terms]

### Why Us
[Only differentiators they reacted to]

**Claims to validate:** [Every claim with no customer evidence]

## Mutual Action Plan (shared table)

| Step | Owner | Target Date | Status |
|------|-------|-------------|--------|
| [Remaining validation] | [us/customer/name] | [date] | [status] |
| [Security review] | | | |
| [Legal redlines] | | | |
| [Procurement] | | | |
| [Signatures] | | | |
| [Internal approvals] | | | |

**Date conflicts:** [Steps whose dates make CloseDate impossible]

## Suggested CRM edits (for the rep to make)
- NextStep → "[next dated step from the plan]"
- CloseDate → [if the backward plan says the current date isn't credible]
[These are recommendations only — this skill reads, it does not write. Make them in Salesforce yourself, or hand editing to a guided-write skill.]

## Champion note (hand to `draft-outreach`)
[The action plan to share, asking the champion to confirm owners on their side — drafting is out of scope here.]
```

Link the opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

**Offer to assemble the artifacts as shareable documents** if a docs connector is present (a capability call, not an SF read — skip silently if absent): the business case as a customer-facing doc, and the mutual action plan as a co-ownable table. Degrade to the inline Markdown above when no docs tool is available.

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a close-plan progress meter and path-to-signature datagrid may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
