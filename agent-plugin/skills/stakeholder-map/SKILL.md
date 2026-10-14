---
name: stakeholder-map
description: "Build a stakeholder map from Salesforce contacts and roles plus email, calendar, calls and Slack, showing influence, stance, gaps and access paths. Use to identify decision makers, assess single-threading or plan introductions. Account brief: account-context."
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

# Stakeholder Map

`account-context` lists contacts; this skill models the deal. Ground → (read + evidence, all in ONE turn) → classify → analyze. **Read-only:** this skill never writes to Salesforce; it produces a map and suggested relationship moves. Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

## 1. Ground and resolve

Ground **only Contact** — it always exists (naming a missing custom object fails the whole call). Its fields reveal this org's role/sentiment/influence schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

For **deal scope**, run Contact ObjectInfo and this resolver in the **same tool turn (parallel)**. Set `%DEALNAME%` to 1–2 words from the opportunity name.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, first: 10) { edges { node { Id Name { value } AccountId { value } Account { Id Name { value } } StageName { value } CloseDate { value } Owner { Id Name { value } } } } } } } }\"}" })
```

Require one Opportunity; if ambiguous, ask the user to choose by name, account, stage, close date, and owner. Keep exact `Id` as `<OPPORTUNITY_ID>` and `AccountId` as `<ACCOUNT_ID>`.

Step 1 is the authority on names — use exact strings from it, never guess. From the result, get: (a) scalar `__c` fields (role, sentiment, influence, seniority, etc.) — take their `{ value }`; (b) any org-specific lookup's exact `relationshipName` to span for a related record's name.

## 2. Read (fill from step 1) — TWO parallel calls for deal scope, ONE for account scope

NEVER combine these into a single query. Run them as separate reads issued in the same turn (parallel). Combining `Contacts` + `Opportunities` with nested `OpportunityContactRoles` in one query will exceed the GraphQL parser's token limit.

**Reference-field rules (avoids the retry loop):**
- A scalar/`__c` field → `Field__c { value }`. `displayValue` is null for Id fields here — don't rely on it.
- To get a **related record's name**, span via the exact `relationshipName` from Step 1. Do NOT append `{ ... }` to a raw `Id`/`__c` field.
- Only span relationships Step 1 actually returned. No usable relationshipName → take the `__c { value }` (the Id) and move on — **do not retry**. `ReportsTo` (standard self-lookup) and the `OpportunityContactRoles`/`Contacts` child relationships below are standard — always available, no grounding needed.

Insert `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed org-specific relationship.

**Deal scope:**

**Call A — OCR contacts on the deal:**

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPPORTUNITY_ID>\\\" } }, first: 1) { edges { node { Id Name { value } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Id Name { value } Title { value } Email { value } Phone { value } ReportsTo { Name { value } Title { value } } <CONTACT_CUSTOM> } } } } } } } } } }\"}" })
```

**Call B — full account contact roster (for gap analysis):**

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, first: 1) { edges { node { Id Name { value } Contacts(first: 50) { edges { node { Id Name { value } Title { value } Email { value } <CONTACT_CUSTOM> } } } } } } } } }\"}" })
```

**Account scope** (`%ACCOUNTNAME%` = 1–2 words from the account name):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNTNAME%\\\" } }, first: 1) { edges { node { Id Name { value } Contacts { edges { node { Id Name { value } Title { value } Email { value } Phone { value } ReportsTo { Name { value } Title { value } } <CONTACT_CUSTOM> <REL_BLOCKS> } } } } } } } } }\"}" })
```

Empty `edges` → broaden `%DEALNAME%`/`%ACCOUNTNAME%`, or ask the user for the right identifier.

## 2b. Evidence (parallel with step 2 after deal resolution)

Issue Call A, Call B, and all of step 2b as tool calls in a single turn. For account scope, issue the Account read and evidence calls together.
- **email**: per contact, last exchange date and direction (did they reply?).
- **calendar**: who has actually attended meetings.
- **docs**: call transcripts — who spoke, what stance they took.
- **slack**: colleagues who have their own relationships at this account.

Use whatever email/calendar/doc/Slack tools are available; skip silently if none are present (SFDC-only is fine). Cite source + date for anything you use.

## 3. Classify each person (cite every claim; invent nothing)

| Person | Title | Deal role | Engagement | Stance | Evidence |
|---|---|---|---|---|---|
| [name] | [title] | Champion / Economic buyer / Evaluator / Influencer / Blocker / Unknown | Active (met <14d) / Warm / Cold / Never met | 🟢 / 🟡 / 🔴 / ? | [last meeting, email reply, transcript quote] |

Rules: a "champion" must have done something for you (made an intro, shared internal info, pushed a meeting) — advocacy in one call doesn't qualify. Mark "Unknown" honestly rather than guessing stance. Required stakeholders for close and target buyer titles are external knowledge — infer from the org's own data or ask the user once, never invent.

## 4. Find the gaps and the paths

- **Missing roles:** which required stakeholders have no identified person (no economic buyer, no security/legal contact, no exec sponsor).
- **Single-thread risk:** how many people have actually engaged in the last 30 days.
- **Access paths to the missing people:** who on the map reports to or works with them (via `ReportsTo`, titles), which colleague has a relationship (from Slack), whether a past champion moved into that org, what a warm intro would look like.
- **Dark contacts:** people who attended meetings or appear in email threads but aren't in SFDC at all — list them so the rep can add them.

## 5. Output — stakeholder map (primary, portable)

Assemble the map as Markdown. This is the deliverable in any host. Cite every claim; quote a blank field as blank; drop contacts you have no data for.

```
# Stakeholder Map: [Opp / Account]

## The map
[classification table from Step 3]

## Coverage verdict
[e.g. "Engaged with 2 of 5 required roles. Economic buyer identified but never met. Single-threaded through [name]."]

## Missing people and how to reach them
1. [Role we're missing] — likely [name/title if known] — path: [warm intro via X / champion ask / direct outreach angle]
2. …

## Not in SFDC yet
- [Name, title, where they appeared] — list them for the rep to add. On a read-only connector, this is a checklist for manual entry.

## This week
- [The single highest-leverage relationship action]
```

Link each Contact inline (`https://[instanceUrl]/lightning/r/Contact/[Id]/view`).

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a power/stance heatmap and stakeholder grid may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
