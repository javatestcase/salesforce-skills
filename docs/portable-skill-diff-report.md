# Portable skill diff report

## Comparison method

This is a mechanical, line-by-line comparison of the current files generated with Python standard-library `difflib.unified_diff` using exactly three context lines (`n=3`). It does not infer semantic equivalence.

- Source: `salesforce-for-sales/skills/<name>/SKILL.md`
- Active: `agent-plugin/skills/<name>/SKILL.md`
- Additions and deletions count `+` and `-` content lines emitted by that same unified diff, excluding file headers.
- Status is `Exact match` when the unified diff is empty and `Approved deviation` only for the three reviewed changes below.

## Inventory

| Inventory item | Count / value |
|---|---|
| Source skills | 34 |
| Active skills | 34 |
| Shared skills | 34 |
| Source-only skills | None |
| Active-only skills | None |
| Byte-identical shared skills | 31 |
| Approved deviations | 3 |

All `display_widget` instructions, renderer JSON, variable contracts, and text fallbacks are preserved. The active tree remains a complete mirror except for the three approved, non-widget deviations documented below.

## Skill summary

| Skill | Source lines | Active lines | Additions | Deletions | Status |
|---|---:|---:|---:|---:|---|
| `account-context` | 880 | 880 | 0 | 0 | Exact match |
| `account-tiering` | 660 | 660 | 0 | 0 | Exact match |
| `calendar-events` | 499 | 499 | 0 | 0 | Exact match |
| `call-follow-up` | 164 | 164 | 0 | 0 | Exact match |
| `call-prep` | 645 | 645 | 0 | 0 | Exact match |
| `close-plan` | 636 | 636 | 0 | 0 | Exact match |
| `configure` | 322 | 322 | 0 | 0 | Exact match |
| `customer-health` | 628 | 628 | 0 | 0 | Exact match |
| `customer-voice` | 68 | 68 | 0 | 0 | Exact match |
| `daily-briefing` | 596 | 596 | 0 | 0 | Exact match |
| `deal-advance-gap` | 596 | 596 | 0 | 0 | Exact match |
| `deal-review` | 940 | 940 | 0 | 0 | Exact match |
| `deal-signals` | 538 | 538 | 0 | 0 | Exact match |
| `deal-slip-scenario` | 627 | 627 | 0 | 0 | Exact match |
| `draft-outreach` | 387 | 387 | 0 | 0 | Exact match |
| `expansion-whitespace` | 740 | 740 | 0 | 0 | Exact match |
| `find-internal-answer` | 53 | 53 | 0 | 0 | Exact match |
| `forecast-narrative` | 635 | 635 | 1 | 1 | Approved deviation |
| `handle-objection` | 55 | 55 | 0 | 0 | Exact match |
| `inbox-sweep` | 451 | 451 | 0 | 0 | Exact match |
| `lead-triage` | 699 | 699 | 1 | 1 | Approved deviation |
| `pipeline-review` | 657 | 657 | 0 | 0 | Exact match |
| `query-activity-history` | 531 | 531 | 0 | 0 | Exact match |
| `renewal-radar` | 756 | 756 | 0 | 0 | Exact match |
| `rep-context` | 482 | 482 | 0 | 0 | Exact match |
| `research-prospect` | 571 | 571 | 0 | 0 | Exact match |
| `salesforce-hygiene-check` | 630 | 630 | 0 | 0 | Exact match |
| `stakeholder-map` | 607 | 607 | 0 | 0 | Exact match |
| `team-pipeline` | 769 | 769 | 0 | 0 | Exact match |
| `update` | 35 | 35 | 0 | 0 | Exact match |
| `using-display-widget` | 306 | 306 | 0 | 0 | Exact match |
| `voice-profile` | 70 | 70 | 0 | 0 | Exact match |
| `weekly-wrap` | 326 | 331 | 13 | 8 | Approved deviation |
| `win-loss-review` | 357 | 357 | 0 | 0 | Exact match |

## Deviation decisions

| Skill | Issue | Exact change | Why necessary | Value |
|---|---|---|---|---|
| `lead-triage` | [#9](https://github.com/salesforce/salesforce-skills/issues/9) | Keep `Owner { ... on User { Name { value } } }` and add the adjacent `... on Group { Name { value } }` fragment. | `Lead.Owner` is a polymorphic User/Group union, so selecting a shared `Name` is invalid and a User-only fragment does not resolve queue ownership. | Both user-owned and queue-owned leads resolve with an owner name. |
| `forecast-narrative` | [#15](https://github.com/salesforce/salesforce-skills/issues/15) | Change only the field-history boundary from `CreatedDate >= %QSTART%` to `CreatedDate >= %QSTART%T00:00:00Z`. | `OpportunityFieldHistory.CreatedDate` requires a DateTime literal, while `%QSTART%` is a date. | The movement fallback executes without changing date-only opportunity filters. |
| `weekly-wrap` | [#16](https://github.com/salesforce/salesforce-skills/issues/16) | Split the single 12-root request into two parallel `dispatch_readonly` calls: six detail roots and six aggregate roots; update only the directly affected recovery wording. | Salesforce GraphQL allows at most 10 data fetchers, so the combined six-detail/six-aggregate request always fails at 12. | Both six-root reads stay under the limit, and an aggregate failure no longer discards detail rows. |

## Complete unified diffs

Only the three differing skills have diff blocks. The headers use the exact relative source and active paths, and every hunk has the three context lines emitted by `difflib.unified_diff(..., n=3)`.

**Whitespace notation:** Inside the rendered diff lines below, U+2420 `␠` represents each terminal ASCII space. This substitution is applied only after diff generation, so terminal whitespace remains visible without introducing trailing whitespace into this report. In particular, an otherwise blank context line is rendered as `␠` because the unified-diff context marker itself is a terminal space.

### `forecast-narrative`

````diff
--- salesforce-for-sales/skills/forecast-narrative/SKILL.md
+++ agent-plugin/skills/forecast-narrative/SKILL.md
@@ -74,7 +74,7 @@
 Prior snapshot pasted → diff it (up / slipped / added / lost). No snapshot → pull this quarter's field history for the delta (SOQL only — `OpportunityFieldHistory` has no GraphQL form), and only skip the section if that too is empty/unavailable:
 ```
 dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
-  queryParams: { "q": "SELECT OpportunityId, Field, OldValue, NewValue, CreatedDate FROM OpportunityFieldHistory WHERE CreatedDate >= %QSTART% AND Field IN ('StageName','Amount','CloseDate') ORDER BY CreatedDate DESC" })
+  queryParams: { "q": "SELECT OpportunityId, Field, OldValue, NewValue, CreatedDate FROM OpportunityFieldHistory WHERE CreatedDate >= %QSTART%T00:00:00Z AND Field IN ('StageName','Amount','CloseDate') ORDER BY CreatedDate DESC" })
 ```
 Derive moved-up / slipped / added / lost from those rows. Per **Commit**/**Best Case** deal, one grounded line — status, what's needed, risk (cite `NextStep`/`LastActivityDate`). Link each deal. **Leader/team rollup across many reps:** cap per-deal commentary to top 5 by Amount per rep.
␠
````

### `lead-triage`

````diff
--- salesforce-for-sales/skills/lead-triage/SKILL.md
+++ agent-plugin/skills/lead-triage/SKILL.md
@@ -50,7 +50,7 @@
 **Lead (by identifier user provided — Id, email, or name+company):**
 ```
 dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
-  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Lead(where: { <LEAD_FILTER> }, first: 1) { edges { node { Id Name { value } Company { value } Title { value } Email { value } LeadSource { value } Status { value } CreatedDate { value } <LEAD_CUSTOM> Owner { ... on User { Name { value } } } } } } } } }\"}" })
+  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Lead(where: { <LEAD_FILTER> }, first: 1) { edges { node { Id Name { value } Company { value } Title { value } Email { value } LeadSource { value } Status { value } CreatedDate { value } <LEAD_CUSTOM> Owner { ... on User { Name { value } } ... on Group { Name { value } } } } } } } } }\"}" })
 ```
␠
 **Account (by company name or domain):**
````

### `weekly-wrap`

````diff
--- salesforce-for-sales/skills/weekly-wrap/SKILL.md
+++ agent-plugin/skills/weekly-wrap/SKILL.md
@@ -46,20 +46,25 @@
   ```
   Capture the Ids as `<TEAM_USER_IDS>`; swap every `scope: MINE` in step 2 for `OwnerId: { in: [<TEAM_USER_IDS>] }`. If your org's team hierarchy isn't ManagerId-based, resolve the roster once from context instead of guessing.
␠
-## 2. Read — pipeline movement + calendar in ONE dispatch; evidence in the SAME turn
-
-**One query, six aliased roots** — closed, new, touched (moved), and closing-next-week Opportunities, plus this-week and next-week meetings. No `OpportunityHistory` read: `LastModifiedDate` on still-open opps is the movement signal, so there's no second object to ground or query. Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields from step 1.
+## 2. Read — pipeline movement + calendar in TWO dispatches; evidence in the SAME turn
+
+**Why two:** a GraphQL request allows at most 10 subqueries ([Salesforce GraphQL query limits](https://developer.salesforce.com/docs/platform/graphql/guide/query-limits.html)). Six detail roots plus six aggregate roots in one request fails with `ExecutionAborted: The number of data fetchers in the query is 12, exceed the data fetcher limitation 10` (verified v60.0–v68.0). Fire the detail read and the aggregate read below as two `dispatch_readonly` GET GraphQL calls in the same parallel tool turn. Don't merge them back into one request.
+
+**Detail read, six aliased roots:** closed, new, touched (moved), and closing-next-week Opportunities, plus this-week and next-week meetings. No `OpportunityHistory` read: `LastModifiedDate` on still-open opps is the movement signal, so there's no second object to ground or query. Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields from step 1.
␠
 ```
 dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
-  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { closedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } newThisWeek: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CreatedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } touchedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } LastModifiedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } closingNextWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } meetingsThisWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } meetingsNextWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } } aggregate { closedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, groupBy: { IsWon: { group: true } }) { edges { node { aggregate { IsWon { value } Id { count { value } } Amount { sum { value } } } } } } newAgg: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } touchedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } } closingAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } meetingsThisWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } meetingsNextWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } } } }\"}" })
+  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { closedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } newThisWeek: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CreatedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } touchedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } LastModifiedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } closingNextWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } meetingsThisWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } meetingsNextWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } } } }\"}" })
+
+dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
+  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { closedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, groupBy: { IsWon: { group: true } }) { edges { node { aggregate { IsWon { value } Id { count { value } } Amount { sum { value } } } } } } newAgg: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } touchedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } } closingAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } meetingsThisWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } meetingsNextWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } } } }\"}" })
 ```
␠
 **Team scope** → swap every `scope: MINE` above for `OwnerId: { in: [\"<TEAM_USER_IDS>\"] }`.
␠
-**Aggregates ride in the SAME query — the `aggregate {}` block above, paired root-for-root with the `query {}` detail (one dispatch, not seven).** The six first:50 `query {}` roots are bounded example rows, not the count/$ source — Net $, won/lost, new, touched (by stage), and closing-next-week counts **and amounts** come from the paired `aggregate {}` roots instead: `closedAgg` (grouped by `IsWon`), `newAgg`, `touchedAgg` (grouped by `StageName`), `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`. The team-scope swap above (`scope: MINE` → `OwnerId: { in: [...] }`) applies to the `aggregate {}` roots too.
-
-**Grouping fallback — only if the combined read errors.** `closedAgg` groups on `IsWon` and `touchedAgg` on `StageName`; grouping a boolean/picklist throws `DataFetchingException` in some orgs. If the query errors on either grouped root, re-fire just that total as a SOQL `GROUP BY` (own scope shown; team scope → `OwnerId IN (<TEAM_USER_IDS>)`), which groups cleanly:
+**Aggregate read: the second dispatch above, paired root-for-root with the `query {}` detail (two dispatches, not twelve).** The six first:50 `query {}` roots are bounded example rows, not the count/$ source — Net $, won/lost, new, touched (by stage), and closing-next-week counts **and amounts** come from the paired `aggregate {}` roots instead: `closedAgg` (grouped by `IsWon`), `newAgg`, `touchedAgg` (grouped by `StageName`), `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`. The team-scope swap above (`scope: MINE` → `OwnerId: { in: [...] }`) applies to the `aggregate {}` roots too.
+
+**Grouping fallback — only if the aggregate read errors.** `closedAgg` groups on `IsWon` and `touchedAgg` on `StageName`; grouping a boolean/picklist throws `DataFetchingException` in some orgs. If the query errors on either grouped root, re-fire just that total as a SOQL `GROUP BY` (own scope shown; team scope → `OwnerId IN (<TEAM_USER_IDS>)`), which groups cleanly:
␠
 ```
 dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
@@ -68,7 +73,7 @@
   queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<CURRENT_USER_ID>' AND IsClosed = false AND LastModifiedDate = THIS_WEEK GROUP BY StageName" })
 ```
␠
-**If the whole combined request returns no usable `data`** — a grouped root's `DataFetchingException` can surface as top-level `errors` with `data` null/absent, taking the other four aggregate roots **and all six detail roots** down with it, not just the grouped total — don't stop at the two SOQL totals. Re-fire the combined request with the two grouped roots removed: keep the six detail `query {}` roots and the four non-grouped `aggregate {}` roots (`newAgg`, `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`), drop `closedAgg` and `touchedAgg`, then take the closed-by-`IsWon` and touched-by-`StageName` totals from the two SOQL `GROUP BY` calls above. That recovers the detail rows and all six totals without the roots that trigger the exception.
+**If the aggregate request returns no usable `data`**, don't stop at the two SOQL totals. A grouped root's `DataFetchingException` can surface as top-level `errors` with `data` null or absent, which takes the other four aggregate roots down with it. The detail read is a separate dispatch, so its rows are unaffected. Re-fire the aggregate request with `closedAgg` and `touchedAgg` removed, keeping the four non-grouped roots (`newAgg`, `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`). Then take the closed-by-`IsWon` and touched-by-`StageName` totals from the two SOQL `GROUP BY` calls above. That recovers all six totals without the roots that trigger the exception.
␠
 If an aggregate root's `count` exceeds 50, label its paired detail root's rows "Top 50 of `<count>`" in step 3 — never derive the count/$ from the capped detail rows themselves. If an aggregate root errors (and the grouping fallback above doesn't apply or also fails), mark that total unavailable and avoid complete-population wording — do **not** fall back to summing/counting the capped rows.
␠
````

## Current verification snapshot

| Check | Result |
|---|---|
| `validate` | PASS |
| Live reads | PASS on `genwatt-demo` |
| E2E | 155/155; guards 4/4 |
| Widget parity | 26/26 |
| Hosted contracts | 26/26 |
| Ravelin browser | 26/26 with 130/130 semantic checks and 59/59 capture-only actions (39 messages, 20 links) |

Quick remains unverified. The official opaque-origin basic-host and Inspector paths retrieve the App/result but stall while rendering; the separate-origin compatible shim renders successfully. The Ravelin result therefore demonstrates compatible-host behavior, not Quick behavior or success in the opaque-origin paths.
