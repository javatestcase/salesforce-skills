---
name: query-activity-history
description: "Build an interaction timeline from closed Salesforce Tasks and Events on one Account, Contact, Lead or Opportunity, with dates, people and notes. Use when inspecting what happened on a record or reviewing its activity. To create an entry, use log-activity."
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

# Query Activity History

Pull and summarize the `ActivityHistory` for ONE `Account`, `Contact`, `Lead`, or `Opportunity` — the timeline of closed Tasks and Events on that record. **Read-only:** this skill never writes to Salesforce; to log an entry, hand off to `log-activity`.

# Rules

- **Only these four parents expose `ActivityHistories`: `Account`, `Contact`, `Lead`, `Opportunity`.** Any other object → stop and tell the user; don't attempt the query.
- `ActivityHistory` is a **child subquery only** — it can't be queried standalone, and UI-API GraphQL doesn't expose it, so this skill uses **SOQL at `v63.0`**. Every field below is standard and fixed; no schema grounding is needed.
- Render `ActivitySubtype` (Call/Email/Task/Event), NOT `ActivityType` — the latter is often empty.
- A blank/absent history is a valid "no activity" result, not an error.

## 1. Validate the object

`objectName` must be one of `Account`, `Contact`, `Lead`, `Opportunity` (key prefixes `001`/`003`/`00Q`/`006`). Anything else → stop, tell the user only those four are supported, don't query.

## 2. Resolve the record

If the user gave an Id matching the object's prefix, use it. Otherwise look up by name (`Name` works for all four — compound for Contact/Lead):

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
         queryParams: { "q": "SELECT Id, Name FROM [objectName] WHERE Name LIKE '%[match]%' LIMIT 5" })
```

- **One match** → use its `Id`. **Multiple** → list (Name · Id) and ask which. **None** → tell the user no `[objectName]` by that name exists; never invent one.

## 3. Query activity history

Subquery from the resolved parent (standard fields, no grounding):

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
         queryParams: { "q": "SELECT (SELECT ActivityDate, ActivitySubtype, ActivityType, CompletedDateTime, Description, Subject, OwnerId, Owner.Name, CreatedById, CreatedBy.Name, WhoId, Who.Name, StartDateTime, EndDateTime, LastModifiedDate FROM ActivityHistories ORDER BY ActivityDate DESC NULLS LAST, LastModifiedDate DESC LIMIT 500) FROM [objectName] WHERE Id = '[recordId]'" })
```

- **On error `"There is an implementation restriction on ActivityHistories"`** (very large history) → retry the exact same query with `LIMIT 500` appended inside the subquery (before the closing `)`).
- Response is one parent record with a nested `ActivityHistories` collection. Absent/empty collection = valid "no activity", not an error.
- Use `ActivitySubtype` for the type; `ActivityType` is often blank.

## 4. Output — activity timeline (primary, portable)

Assemble the timeline as Markdown. This is the deliverable in any host. Apply the formatting rules below.

```markdown
# Activity History: [RecordName] ([ObjectName])
**[TotalCount] activities**  |  **Last:** [LastActivityDate]  |  **Owner:** [OwnerName]

| Date | Type | Subject | Owner | With |
|---|---|---|---|---|
| [ActivityDate] | [ActivitySubtype] | [Subject] | [Owner.Name] | [Who.Name or —] |
| … | | | | |
```

- One row per activity, most recent first (sorted by `ActivityDate` desc, then `LastModifiedDate` desc).
- Show at most **20**; if `TotalCount > 20` append `…and [N] older activities not shown`.
- `TotalCount = 0` → render only `No activity history found for [RecordName].`
- Label undated activities "Undated"; omit the "With" cell when `Who.Name` is null.
- Append each non-empty `Description` as a short sub-bullet under its row (truncate at 200 chars), or add a Description column inline — don't drop it.

Link the record inline (`https://[instanceUrl]/lightning/r/[ObjectName]/[Id]/view`).

## 5. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a cadence-heatmap/timeline visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 4 is the whole deliverable.
