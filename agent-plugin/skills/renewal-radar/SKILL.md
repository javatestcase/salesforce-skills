---
name: renewal-radar
description: "Build a renewal risk brief from Salesforce opportunities, email, documents and Slack, covering timing, activity, uplift and next moves. Use to scan upcoming renewals or prepare one renewal motion; for overall account health or QBR prep, use customer-health."
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

# Renewal Radar

The renewal you start 90 days out is a process; the one you notice 2 weeks out is a discount. Keep the renewal calendar visible, flag the risky ones early, prep each renewal motion. **Read-only:** this skill never writes to Salesforce; it surfaces renewals and suggests changes for the rep to apply themselves.

**Inputs:** my book (default), named rep, named account, or the team. Window: next N days (default 120), or specific quarter (Q1/Q2/Q3/Q4 FY26 → compute start/end dates).

**Empty owned book → fail fast, then ask which scope.** If the my-book read (the `OwnerId` filter) returns zero renewals, do not drop the owner filter and go org-wide on your own. Stop, say their own book came back empty, and ask which scope they want instead (org-wide, a named rep, or a named account) before re-running, then wait. Never invent records.

## 1. Resolve scope (if named rep)

- **"my renewals"** (default) → resolve `currentUser.Id` once through this exact query, then use that ID for the OwnerId filter:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql", queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })
  ```
- **"[Rep]'s renewals"** → resolve one User. Shared/demo orgs collide (one name → base user + regional variants like `(AM)`/`(BK)`). Pull enough to disambiguate:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Email { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id for the OwnerId filter in step 3. **Several** → list them (Name · Email · active? · Id) and ask user to pick. **Zero** → ask user to clarify.
- **Named account** → resolve Account by name, use AccountId filter in step 3.
- **Team** → no owner filter.

## 2. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists. Its fields reveal this org's renewal-specific custom signals.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

From the result, select only relevant `__c` fields (ARR, renewal type, usage signals, auto-renew flags) and take their `{ value }`.

## 3. Pull renewal calendar (GraphQL — fill from step 2)

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields from Step 2. **Nest Account and Owner in this one query.**

**Date filter:** user can specify window as "next N days" (default 120) or "Q1 FY26" / "Q2 FY26" etc.
- **"next N days"** → use `CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 120 } } }`
- **"Q1 FY26"** → compute quarter ISO dates, use `CloseDate: { gte: { value: "2026-02-01" }, lte: { value: "2026-04-30" } }`

**Primary query (`like`/`or` catches both Type picklist values and Name patterns) — ONE combined dispatch: a bounded `query` for the detail rows plus an `aggregate` sibling on the IDENTICAL `where` for the authoritative total renewal ARR + count.** Do not sum the capped `query` rows for the headline total — read it from the `aggregate` block's `Amount.sum.value` / `Id.count.value` (or `totalCount`).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { eq: \\\"<currentUserId>\\\" }, IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 120 } } }, or: [{ Type: { like: \\\"%renew%\\\" } }, { Name: { like: \\\"%renew%\\\" } }] }, orderBy: { CloseDate: { order: ASC } }, first: 50) { edges { node { Id Name { value } Type { value displayValue } Amount { value displayValue } CloseDate { value } StageName { value displayValue } NextStep { value } LastActivityDate { value } Account { Name { value } Industry { value displayValue } Type { value displayValue } } Owner { Name { value } } <OPP_CUSTOM> } } } } aggregate { Opportunity(where: { OwnerId: { eq: \\\"<currentUserId>\\\" }, IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 120 } } }, or: [{ Type: { like: \\\"%renew%\\\" } }, { Name: { like: \\\"%renew%\\\" } }] }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

Replace the `CloseDate` clause in **both** the `query` and `aggregate` blocks with the computed date filter — keep the two `where` clauses identical. Insert `<OPP_CUSTOM>` as `ARR__c { value } AutoRenew__c { value }` if those fields exist, or omit if none (on the `query` block only — the `aggregate` block doesn't select record fields). If `aggregate.Opportunity.totalCount` exceeds the 50 detail rows returned, label the calendar "Top 50 of `<totalCount>`" — never present the 50-row slice as the complete renewal book.

**Scope filters (apply identically to BOTH the `query` and `aggregate` `where`):**
- **My book** (default): keep `OwnerId: { eq: "<currentUserId>" }` using the `currentUser.Id` resolved in step 1
- **Named rep**: replace it with `OwnerId: { eq: "<resolvedUserId>" }`
- **Named account**: replace it with `AccountId: { eq: "<accountId>" }`
- **Team**: omit the owner clause

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

**Issue step 3 and all of step 3b as tool calls in a single turn.** They're independent (searches key on account names, not the SF result):
- **email**: threads mentioning each account name in last 90d → escalations, sentiment, exec engagement.
- **docs**: docs mentioning account names → prioritize files with "escalation", "churn", "expansion" in title, most recent first. Read top 1–2 per account and extract: risk signals, expansion discussions.
- **slack**: account names in last 30d → internal context (support escalations, CSM warnings, expansion threads).

Use whatever email/doc/Slack search tools are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use.

**Perf guardrail:** Do NOT fire additional SF reads for `Task` or `Contract` — the step 3 read has the data.

## 4. Score each renewal

| Signal | Effect |
|---|---|
| No activity on the account in 30+ days (LastActivityDate < 30 days ago) | risk ↑ |
| Open support escalation mentioned in email/Slack | risk ↑ |
| Usage/adoption signals trending down (if `__c` field present) | risk ↑ |
| Active expansion conversation in email/Slack | risk ↓ / uplift ↑ |
| Multi-year or auto-renew term (if `__c` flag present) | risk ↓ |
| NextStep blank or stale | risk ↑ |
| Champion or economic buyer has changed/left (email/Slack evidence from 3b) | risk ↑ |

Verdict per renewal: 🟢 on track / 🟡 needs attention / 🔴 at risk — with the evidence.

## 5. Output — renewal radar (primary, portable)

Assemble the radar as Markdown. This is the deliverable in any host. Cite the source per row; quote blank fields as blank rather than inventing.

- **Sample vs. book scope — risk verdicts are sampled.** The verdicts and at-risk share are computed from the scored detail rows only; only the ARR/count totals come from the aggregate and cover the full book. When the book exceeds the returned rows, say so in the header (e.g. "Risk shown for top 50 of 180 renewals") and carry the full-book ARR/count there — never present the verdicts as covering the whole book.
- **Specify date window:** e.g. "Aug 4 – Dec 1, 2026" (not just "next 120 days").
- **Status column:** extract from NextStep/Description/custom fields if present (e.g. "Ali resell", "Out of ext."), else fall back to StageName.
- **Timeline specifics in At-risk section:** days until close, months since last activity, field labels for data discrepancies.

```
# Renewal Radar — [scope] — [date range] ([instanceUrl])

| Account | Opp | Renewal date | ARR/Amount | Status | Risk driver | Next step |
|---|---|---|---|---|---|---|
| [Account] | [↗](https://[instanceUrl]/lightning/r/Opportunity/[Id]/view) | [date] | $[X] | [extracted status] | [flag] | [action] |

## At risk (act this week)
- **[Account] [↗](url)** — [date] ([N days away]) — [specific risk with timeline context: "no activity in 2.5 months", "6 days away"] → [the play]

## Uplift candidates
- **[Account] [↗](url)** — [the expansion signal and the proposed uplift motion]

## Suggested SFDC changes (for the rep to apply)
- **Missing NextStep** — [Opp Name]: current NextStep blank → suggested next action based on stage and date proximity.
- **Incorrect CloseDate** — [Opp Name]: current close date [wrong date] → corrected date based on contract/renewal timing.
- **Missing renewal opportunity** — an account whose term is ending with no renewal opp on the books: flag it so the rep can add one ("[Account] – [Year] Renewal", Type Renewal, prior ARR, close at term end).

Present these as suggestions only; this skill does not modify Salesforce. On a read-only connector they are a checklist for the rep to apply manually.
```

For a single named account, expand into a renewal prep brief: history, current sentiment, pricing/uplift recommendation, paperwork timeline worked back from the end date.

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a renewal-calendar/risk visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
