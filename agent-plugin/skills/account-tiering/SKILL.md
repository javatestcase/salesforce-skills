---
name: account-tiering
description: "Rank an account list or full book into action tiers from Salesforce ICP fit, engagement, activity, contact, and opportunity data. Use to score accounts, prioritize coverage, decide where to focus, or identify accounts to activate, qualify, or deprioritize."
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

# Account Tiering

Ground (its own turn) → (read + evidence, all in ONE turn) → score → tier. Scope: "my accounts", a named list, or a report/list view name. Default tier count: 3 (A/B/C). **Read-only:** this skill never writes to Salesforce; it scores and links records, and hands any drafting to `draft-outreach`.

## 1. Ground (hardcoded — Account only)

Ground **only Account** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's real ICP/engagement schema (custom fit score, territory, renewal fields, etc.) — don't assume custom field names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

**Field policy.** Step 2's standard fields and child spans are fixed — always read, never grounded. Custom fields are optional and come from THIS result only: use exact strings, never guess. Select relevant scalar `__c` fields carrying ICP-fit/engagement signals as `{ value }`, and each relevant custom lookup's exact `relationshipName` for a related record name. Build Step 2 only once this result is in hand — never fire the two together.

**Standard-field fallback.** If Step 1 errors, returns no `fields`, or was saved to a file you could not read in full (read failed, truncated, or token-capped), select NO custom fields — not from a preview, a partial read, or memory. Leave `<ACCOUNT_CUSTOM>` and the custom lookup blocks empty, fire Step 2 exactly as written, and disclose it (Step 5).

The ICP (industries, size, titles, disqualifiers) is set in Step 3 by a fixed rule — never invent it.

## 2. Read (fill from step 1, one dispatch)

`%SCOPE%` = `scope: MINE` for "my accounts"; `where: { Name: { in: [\\\"Acme\\\", ...] } }` for a named list. (A report/list-view scope needs its own name→Id resolve first — outside the common path; ask for a name list instead if one isn't already resolved.)

**Reference-field rule:** a confirmed scalar `__c` field → `Field__c { value }` (`displayValue` is null for Id fields here — don't rely on it). For a related record's name, span only the exact `relationshipName` from Step 1: `<relationshipName> { Name { value } }`. No usable `relationshipName` → take the `__c { value }` Id and move on; do not retry.

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields relevant to fit/engagement; `<REL_BLOCKS>` = one block per confirmed relevant custom lookup. `Owner`/`Opportunities`/`Contacts` always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(%SCOPE%, first: 200, orderBy: { Id: { order: ASC } }) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } Website { value } Type { value } LastActivityDate { value } <ACCOUNT_CUSTOM> Owner { Name { value } } <REL_BLOCKS> Opportunities(where: { IsClosed: { eq: false } }, first: 1, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Title { value } } } } } } pageInfo { hasNextPage } totalCount } } } }\"}" })
```

`Opportunities` is an existence check: Salesforce applies the open filter, and `first: 1` returns just the open deal with the earliest close date (it may be past due) — show it in the Open Opp column. Step 4's "Open opportunity exists" = a non-empty `Opportunities.edges`. This read supports no opportunity counts or pipeline amounts, so the output shows none — never count these rows or present one deal as the account's pipeline. Empty `Account` `edges` → for `scope: MINE`, follow the empty-`MINE` rule; for a named list, confirm the account names.

**Bounds.** `Account(first: 200)` is the whole book up to 200 accounts. `pageInfo.hasNextPage: true` → the book is larger (`totalCount` accounts): tier the 200 you have and disclose the partial book (Step 5) — never call them the whole book. `Contacts(first: 10)` is a bounded sample per account — enough for the 3+ contacts signal; a full 10 with no target title scores the persona check `maybe`, not `none`.

## 2b. Evidence (fired IN PARALLEL with step 2 — same turn)

Issue step 2 and step 2b together in one turn; don't wait for the SF read. Keyed on the account scope (names/domains), not the SF result:
- **email**: inbound threads from account domains in the last 90d → which accounts, last date
- **docs/slack**: any account mentions → triggers, concerns

Use whatever tools are available; skip silently if none (SFDC-only is fine). Never block on these; cite source + date for anything you use.

## 3. Score ICP fit (0-10)

**ICP source** — use the first that applies, and record which (Step 5):
1. **Stated** — the industries, size, titles, or disqualifiers the user gives in the request (or earlier in the conversation).
2. **Derived** — otherwise, from the accounts read in Step 2 that have an open opportunity (Step 4's signal), ignoring nulls: target industries = their 3 most common `Industry` values (ties alphabetical); size range = their min–max `NumberOfEmployees`. Persona = a Contact title containing VP, Director, Head, or Chief, or a C-level acronym (CEO, CFO, CRO, CIO, CTO, COO). Disqualifiers = none, so every account scores clean.
3. **Ask** — the ICP can't be derived: no account has an open opportunity, or none of those accounts has an `Industry` or none has a `NumberOfEmployees` value. Ask the user for the ICP once, and don't score until they answer — never derive with a missing criterion.

A criterion the user didn't state falls back to its derived value; if that value can't be derived, ask (3).

| Signal | Weight | Scoring |
|---|---|---|
| Industry match | 3 | exact=3, adjacent=1, off-ICP=0 |
| Size in range | 3 | in range=3, ±50%=1, outside=0 |
| Target persona present (Contact titles) | 2 | yes=2, maybe=1, none=0 |
| No disqualifiers | 2 | clean=2, soft DQ=1, hard DQ=0 |

## 4. Score engagement (0-10)

| Signal | Weight | Scoring |
|---|---|---|
| Open opportunity exists (Step 2) | 3 | yes=3, no=0 |
| LastActivityDate recency | 3 | <30d=3, 30-90d=2, 90-180d=1, >180d=0 |
| Inbound signal (Step 2b email, last 90d) | 2 | yes=2, no=0 |
| Multiple contacts engaged | 2 | 3+=2, 2=1, ≤1=0 |

## 5. Tier and recommend

Plot on a 2x2 (Fit × Engagement). **High = 6 or more** on that axis; low = 5 or less.
- **Tier A** (high fit, high engagement): active pursuit — progress the open opp, multi-thread.
- **Tier B** (high fit, low engagement): activation — outbound sequence, find a trigger.
- **Tier C** (low fit, high engagement): qualify hard — one discovery call to confirm fit or DQ.
- **Deprioritize** (low fit, low engagement): no active motion, revisit quarterly.

**Disclosures** — carry each that applies into the output, as a line under the heading:
- Partial book (`hasNextPage: true`): "first 200 of [totalCount] accounts — narrow the scope to tier the rest". The heading also counts "200 of [totalCount]", never just 200.
- Standard-field fallback: "custom fit fields unavailable — scored on standard fields".
- Derived ICP: "ICP derived from your [N] accounts with open deals: [industries], [min–max] employees". Omit when the user stated the ICP.

## 6. Output — tiering plan (primary, portable)

Assemble the tiering plan as Markdown. This is the deliverable in any host. Never emit empty rows or invented records; drop any tier with no accounts.

```
# Account Tiering - [N] accounts

## Tier A - Active Pursuit ([N])
| Account | Fit | Eng | Open Opp | Last Touch | Next Action |
|---|---|---|---|---|---|
...

## Tier B - Activate ([N])
...

## Tier C - Qualify or DQ ([N])
...

## Deprioritized ([N])
[Just names, collapsed]

## Coverage Gaps
- [N] Tier A/B accounts with no activity in 30+ days
- [N] accounts missing Industry or NumberOfEmployees (can't score - fix in SFDC)
```

Link each account inline (`https://[instanceUrl]/lightning/r/Account/[Id]/view`). Lead with the single biggest coverage gap or highest-leverage move as a one-line callout above the tiers.

## 7. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a fit×engagement heatmap and tier breakdown may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 6 is the whole deliverable.
