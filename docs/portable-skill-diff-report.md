# Portable skill diff report

## Comparison method

This is a mechanical, line-by-line comparison of the current files generated with Python standard-library `difflib.unified_diff` using exactly three context lines (`n=3`). It does not infer semantic equivalence.

- Source: `salesforce-for-sales/skills/<name>/SKILL.md`
- Active: `agent-plugin/skills/<name>/SKILL.md`
- Additions and deletions count `+` and `-` content lines emitted by that same unified diff, excluding file headers.
- Status is `Exact match` when the unified diff is empty and `Approved deviation` only for the twelve reviewed skill differences below.

## Inventory

| Inventory item | Count / value |
|---|---|
| Source skills | 34 |
| Active skills | 34 |
| Shared skills | 34 |
| Source-only skills | None |
| Active-only skills | None |
| Byte-identical shared skills | 22 |
| Approved deviations | 12 |

All `display_widget` instructions, renderer JSON, and text fallbacks are preserved. The active
`calendar-events` variable contract has one approved subtitle correction; the active tree remains
a complete mirror except for the twelve reviewed skill deviations documented below.

## Skill summary

| Skill | Source lines | Active lines | Additions | Deletions | Status |
|---|---:|---:|---:|---:|---|
| `account-context` | 880 | 896 | 16 | 0 | Approved deviation |
| `account-tiering` | 660 | 685 | 25 | 0 | Approved deviation |
| `calendar-events` | 499 | 499 | 8 | 8 | Approved deviation |
| `call-follow-up` | 164 | 164 | 0 | 0 | Exact match |
| `call-prep` | 645 | 645 | 0 | 0 | Exact match |
| `close-plan` | 636 | 636 | 0 | 0 | Exact match |
| `configure` | 322 | 322 | 0 | 0 | Exact match |
| `customer-health` | 628 | 636 | 13 | 5 | Approved deviation |
| `customer-voice` | 68 | 72 | 4 | 0 | Approved deviation |
| `daily-briefing` | 596 | 600 | 11 | 7 | Approved deviation |
| `deal-advance-gap` | 596 | 604 | 14 | 6 | Approved deviation |
| `deal-review` | 940 | 955 | 17 | 2 | Approved deviation |
| `deal-signals` | 538 | 546 | 8 | 0 | Approved deviation |
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

| Skill | Evidence | Exact change | Why necessary | Value |
|---|---|---|---|---|
| `account-context` | Synthetic Quick trace | Add canonical deep-query substitution, structural preservation, and one standard-field rebuild rule. | Quick reconstructed the valid source query, unbalanced braces, and moved `aggregate` under `query`. | Quick completed a fresh run without a repair loop while preserving the source query and renderer. |
| `account-tiering` | Synthetic Quick traces | Use the source `>=6` boundary for a binary heatmap and omit unavailable ARR/Whitespace fields instead of inserting zeroes. | Quick introduced a conflicting three-band visualization and fabricated `$0.00` values for unavailable metrics. | Tier and visual totals reconcile, and missing currency remains absent rather than becoming a value. |
| `lead-triage` | [#9](https://github.com/salesforce/salesforce-skills/issues/9) | Keep `Owner { ... on User { Name { value } } }` and add the adjacent `... on Group { Name { value } }` fragment. | `Lead.Owner` is a polymorphic User/Group union, so selecting a shared `Name` is invalid and a User-only fragment does not resolve queue ownership. | Both user-owned and queue-owned leads resolve with an owner name. |
| `forecast-narrative` | [#15](https://github.com/salesforce/salesforce-skills/issues/15) | Change only the field-history boundary from `CreatedDate >= %QSTART%` to `CreatedDate >= %QSTART%T00:00:00Z`. | `OpportunityFieldHistory.CreatedDate` requires a DateTime literal, while `%QSTART%` is a date. | The movement fallback executes without changing date-only opportunity filters. |
| `weekly-wrap` | [#16](https://github.com/salesforce/salesforce-skills/issues/16) | Split the single 12-root request into two parallel `dispatch_readonly` calls: six detail roots and six aggregate roots; update only the directly affected recovery wording. | Salesforce GraphQL allows at most 10 data fetchers, so the combined six-detail/six-aggregate request always fails at 12. | Both six-root reads stay under the limit, and an aggregate failure no longer discards detail rows. |
| `calendar-events` | [#20](https://github.com/salesforce/salesforce-skills/issues/20) | Enrich `What` with runtime type, IDs, and Opportunity grounding fields; remove the unsupported attendee count from the active subtitle. | The source projection cannot ground deal output, and `Who` is not an attendee collection. | Deal links/values derive only from returned Opportunity data, and the active subtitle makes no unsupported attendee claim. |
| `customer-health` | Synthetic Quick trace; [#21](https://github.com/salesforce/salesforce-skills/issues/21) | Strengthen the active literal-template rule with pre-dispatch nested-JSON/brace validation and one canonical standard-field rebuild. Add aggregate case totals to the deep read and take every Support count from them. Show `account-context`'s object-not-string `widgetDefinition` example at the widget call. | Quick reconstructed the otherwise valid deep Account request and sent a syntax error before recovering. Separately, the source computes Support from a ten-row Case sample, and Quick once sent the widget as a JSON string. | The first dispatch preserves a validated canonical request, and Support reflects every Case in the window. |
| `customer-voice` | Synthetic Quick trace | Add two rules: quotes come only from docs and email, with no Salesforce reads beyond the three scoping reads; with no quote, keep the template with 0 quotes, the topic, and the period, write `None` under Accounts represented, and offer at most one in-skill next step. | With no quotes in docs or email, Quick searched Salesforce activity the skill does not document, beyond the scoped accounts, and reported a page-capped count. | A zero-quote result stays within the skill's sources and reports no unscoped or capped Salesforce counts. |
| `daily-briefing` | Synthetic Quick trace; [#22](https://github.com/salesforce/salesforce-skills/issues/22) | Copy closing-soon and past-due row names from the returned values, using the Opportunity Name unchanged when it already begins with the Account Name. Select Event `AccountId` in the calendar read and pass those Ids to the meeting-account read. When an email tool is available, run and report the inbox checks; otherwise say they were not run. | The source's `<Account> — <Opp Name>` format repeats the account when names already carry it; Quick rewrote the names and gave one row a name no record has. Separately, no documented read maps an Opportunity-linked meeting to its Account, and Quick once skipped the inbox checks and dropped their section without saying so. | Row names match the queried records without hand editing, Opportunity-linked meetings resolve to their Account through documented reads, and the inbox result is always stated. |
| `deal-advance-gap` | Synthetic Quick traces; [#23](https://github.com/salesforce/salesforce-skills/issues/23); [#24](https://github.com/salesforce/salesforce-skills/issues/24) | Search open deals only in the step 2a name lookup, select `totalCount`, and narrow once when the list is cut off. Return the stage order in step 1 and take the default target from it. Rest row states on returned tasks and events, and label unsourced exit criteria as suggested steps. | Matching 1–2 words oldest-first in 10 rows, closed deals included and with no total, filled the list with old closed deals and omitted the requested open deal. Separately, no documented read returns the stage order behind the default target, and Quick twice showed unsupported row states and scored invented exit criteria. | The named open deal is found, or the agent knows the list is partial and narrows before asking; the target stage matches the org; and the checklist claims only what the data supports. |
| `deal-review` | Synthetic Quick trace; [#26](https://github.com/salesforce/salesforce-skills/issues/26); [#24 follow-up](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032) | Select `totalCount` in the step 2 deal read; when it is above 1, run a documented candidate read, narrowed first by words from the request when more than 10 match, and take the one exact name match or the one open candidate, else ask without offering a cut-off list. Return the stage order in step 1 and take the stage tile from it. | The 1–2 word read takes the latest-closing match with no count, so a two-word phrase returned another rep's $21K deal and the account name a different deal on the same account. Separately, no read returns the stage order behind the stage tile, which a Quick run filled with "mid-funnel" instead of the stages left. | The review covers the requested deal or asks which is meant, and the stage tile matches the org's stage order. |
| `deal-signals` | Synthetic Quick trace; [#25](https://github.com/salesforce/salesforce-skills/issues/25) | Return the step 5 digest for book and team sweeps instead of calling `display_widget`, and drop the chart-and-meter column from a single-deal widget. Fire Stale commitment from the fetched `LastModifiedDate`, state a skipped email search, and list every flagged deal in the digest. | The widget needs a single deal's composite score and six-week trend that no step computes, so a book sweep could only fabricate them or skip the widget. Separately, Quick missed every stale next step, silently skipped the email evidence, and later dropped flagged deals to shorten the digest. | No score or trend is invented, a 39-day-old next step is flagged, an unchecked inbox is never implied clear, and no flagged deal is left out. |

## Deviation details

The three historic source corrections retain their full unified-diff blocks below. The other
deviations are summarized from their exact mechanical diffs and deterministic tests.
The approved `calendar-events` delta is eight additions and eight deletions: it enriches the active
Event `What` projection, adds a concise grounding rule, and removes the unsupported attendee metric
from the active variable contract and subtitle. The dynamic renderer JSON remains byte-identical
to upstream, and `active_widget_templates.py` asserts that no other calendar contract field
changes. The `customer-health` delta is thirteen additions and five deletions: a canonical-query preflight
rule, aggregate case totals in the same deep read, and a widget-payload example. The
`customer-voice` delta is four additions: two local rule paragraphs, each with a blank separator.
The `daily-briefing` delta is eleven additions and seven deletions: row-name and inbox-check rules,
each with a blank separator, and five one-line meeting-account edits. The diff also reports an
unchanged code fence and blank line between two edited lines as replaced. The `deal-advance-gap`
delta is fourteen additions and six deletions: four edited lines, one added branch, one added
self-check item, and three added paragraphs with blank separators, with an unchanged code fence
and blank line between edits also reported as replaced. The `deal-review` delta is seventeen
additions and two deletions: two edited query lines, a stage-order paragraph, and a multiple-match
block (a rule with four bullets, a keep-or-rerun paragraph, and a four-line candidate read), with
blank separators. The `deal-signals` delta is eight additions: four local rule paragraphs, each
with a blank separator.

**Whitespace notation:** Inside the rendered diff lines below, U+2420 `␠` represents each terminal ASCII space. This substitution is applied only after diff generation, so terminal whitespace remains visible without introducing trailing whitespace into this report. In particular, an otherwise blank context line is rendered as `␠` because the unified-diff context marker itself is a terminal space.

### `account-context`

The active mirror adds 16 lines of Quick/Kiro-only canonical-query guidance. The GraphQL document
and renderer remain unchanged. It constrains substitutions to the documented placeholders,
preserves `query` and `aggregate` as siblings, and allows one rebuild from the literal
standard-field form rather than brace repair.

### `account-tiering`

The active mirror adds 25 lines of Quick/Kiro-only hydration guidance. It uses the source `>=6`
threshold for a binary 2×2 heatmap, requires heatmap/tier totals to reconcile, and omits unavailable
ARR or Whitespace fields and columns instead of defaulting them to zero. The Salesforce reads and
renderer remain unchanged.

### `calendar-events`

The active mirror applies the approved [#20](https://github.com/salesforce/salesforce-skills/issues/20)
correction only:

- `What` now returns `__typename`, typed IDs, and the Opportunity fields needed to ground a deal
  link, amount, stage, close date, and Account name.
- The active rule permits deal classification only for `What.__typename == "Opportunity"` and
  requires unavailable/non-deal rendering for every other result.
- The active subtitle omits the unsupported attendee metric. Its variable-contract delta is
  limited to the subtitle wording; the renderer JSON remains byte-identical to upstream.

The mechanical comparison is 8 additions and 8 deletions at 499 lines in both source and active
files. `agent-plugin/evals/mcp_apps/active_widget_templates.py` reconstructs the expected active
contract from the upstream contract and rejects any extra calendar widget delta.

### `customer-health`

The active mirror carries three changes:

- **Quick/Kiro canonical-query safeguard.** Before the first dispatch, the host must preserve the
  literal nested `queryInput`, resolve only documented placeholders, and validate JSON and bracket
  balance. A syntax failure triggers one rebuild from the same standard-field literal, not
  in-place brace repair. A fresh Quick rerun completed its reads on the first attempt.
- **Case-total correction ([#21](https://github.com/salesforce/salesforce-skills/issues/21)).** The deep read adds `aggregate` roots for
  matching accounts, total, open, Escalated, and High/Critical Cases, using the same account
  predicate and 90-day window as the ten detail rows. Support counts come from those totals; the
  rows are described only as the latest ten. When the name matches several accounts, the request
  is rerun by exact Id. The endpoint, existing fields, and widget template are unchanged.
- **Widget payload example (Quick/Kiro adaptation).** Quick once sent `widgetDefinition` as a JSON
  string. The active skill now shows `account-context`'s WRONG/RIGHT payload pair at the widget
  call; the widget template is unchanged.

The mechanical comparison is 13 additions and 5 deletions: 628 source lines and 636 active lines.
Eight deterministic tests cover the local wording, canonical materialization, aggregate placement
and filters, the exact-Id form, and the payload example. Live name and exact-Id reads and a Quick rerun returned totals matching an independent
count. The first Quick run with the payload example made one successful widget call; more runs
are needed because the original failure was intermittent.

### `customer-voice`

The active mirror adds two Quick/Kiro-only rules and changes no query or output template:

- **Sources.** Quotes come only from the docs and email searches. Salesforce stays limited to the
  three scoping reads, with no Task, Event, Case, or other record search as a substitute source
  and no counts from one.
- **No quotes found.** The output keeps the template with 0 quotes, the topic, and the period,
  writes `None` under Accounts represented, fills Gaps, and offers at most one next step: a wider
  period or scope, or a transcript, notes doc, or email thread to search.

The mechanical comparison is 4 additions and 0 deletions: 68 source lines and 72 active lines.
Four deterministic tests check the rule placement and wording, the three documented scoping reads,
and that removing the two rules restores the source byte-for-byte. The documented reads pass in the
exact-call runner. A normal Quick rerun of the same prompt followed both rules.

### `daily-briefing`

The active mirror carries three changes and leaves the renderer JSON unchanged:

- **Inbox check (Quick/Kiro adaptation).** When an email tool is available, the inbox read and
  the "you owe them" search run as part of the briefing. Their result goes in the follow-ups stat
  and inbox block, with `inboxClear` when nothing is found; if they cannot run, the briefing says
  the inbox was not checked instead of dropping the section.
- **Row names (Quick/Kiro adaptation).** Closing-soon and past-due row names are copied from the
  returned values. The Opportunity Name is used unchanged when it already begins with the Account
  Name; otherwise the source's `<Account> — <Opp Name>` format applies. Names are never retyped,
  shortened, or reworded.
- **Meeting-account correction ([#22](https://github.com/salesforce/salesforce-skills/issues/22)).** The calendar read also selects Event
  `AccountId`, which Salesforce derives from the related record. The meeting-account read takes
  those Ids, so Opportunity-linked meetings resolve to their Account through documented reads; the
  domain match remains the fallback. The step 3 placeholder is now `<Event AccountId 001…>`.

The mechanical comparison is 11 additions and 7 deletions: 596 source lines and 600 active lines.
That covers five edited lines and two two-line rules; the unified diff also reports an unchanged
code fence and blank line between two edited lines as replaced. Nine deterministic tests cover the
row-name and inbox-check rules, the Event `AccountId` selection, the meeting-account read, and an
exact source-plus-changes reproduction of the active file. Static
validation, widget parity, the offline widget contract, and the documented reads (7/7) pass. On
the synthetic org, the source reads left two Opportunity-linked meetings with no Account Id or
domain to match; the corrected reads resolved them to their Account and its two open
Opportunities. Two Quick reruns listed both open deals on the meeting's account and rendered all
13 row names exactly as stored. The first made no email call, which led to the inbox-check rule;
the second checked email and reported the inbox.

### `deal-advance-gap`

The active mirror carries four changes and leaves the renderer JSON unchanged:

- **Name lookup ([#23](https://github.com/salesforce/salesforce-skills/issues/23)).** The step 2a
  candidate query searches open deals only (`IsClosed: { eq: false }`) and selects `totalCount`.
  When `totalCount` exceeds the rows returned, the list is treated as cut off and the search is
  narrowed once, for example with the account name, instead of asking the user to choose from it.
  When the request names the account as well as the deal, the search includes both.
- **Stage order ([#24](https://github.com/salesforce/salesforce-skills/issues/24)).** The step 1 request adds an aliased `stages` root that
  returns the Stage picklist in the org's order from the master record type, in the same call. The
  default target is the stage that follows the deal's current stage in that list.
- **Row states (Quick/Kiro adaptation).** Done, In motion, and Scheduled states rest only on
  returned tasks and events; a step held only as Next Step text, or a completed touch awaiting a
  reply, is Not started. A widget self-check also requires each In motion or Scheduled row to name
  its task or event, or be set to Not started.
- **Suggested steps (Quick/Kiro adaptation).** Unless the user names exit criteria, the checklist
  is presented as suggested steps based on the deal's own data, including in `headerSubtitle` and
  `meterValueLabel`. The renderer's fixed "Exit criteria met" meter label is unchanged.

The mechanical comparison is 14 additions and 6 deletions: 596 source lines and 604 active lines.
That covers four edited lines, one added branch, one added self-check item, and three added
paragraphs with blank separators; the unified diff also reports an unchanged code fence and blank
line between edits as replaced. Eleven deterministic tests cover an exact source-plus-changes
reproduction, both source gaps, the materialized candidate and grounding reads, the branch order,
both rules, and the self-check. Static validation,
widget parity, the offline widget contract, and the documented reads (5/5) pass. On the synthetic
org, the source lookup for a two-word phrase returned 10 closed deals without the requested open
deal; the corrected lookup reported 19 open matches for 10 rows, and adding the account name
returned only the requested deal. The corrected step 1 returned the org's ten stages in order, with
Id. Decision Makers after Value Proposition. A second org reproduced both issues' minimum setups
through the Headless 360 `dispatch_readonly` tool. Quick reruns detected the cut-off list and
narrowed by account to the requested deal, named Id. Decision Makers as the next stage, and
labeled the checklist as suggested steps. One row was still marked In motion without an open task,
which led to the self-check; the next rerun marked every open row Not started.

### `deal-review`

The active mirror carries two corrections and leaves the renderer JSON unchanged:

- **Multiple matches ([#26](https://github.com/salesforce/salesforce-skills/issues/26)).** The step
  2 read selects `totalCount`. When it is above 1, a documented candidate read (`first: 10`, with
  `Id`, `Name`, `StageName`, `CloseDate`, `IsClosed`, and `Account.Name`) runs before the result is
  used. When more than 10 deals match, the phrase is first narrowed with the account or other words
  from the request, never with a name from a returned deal. The one candidate whose name equals the
  requested deal is taken, or else the one open candidate; otherwise the candidates are listed and
  the user is asked. An empty or still cut-off list, or a request with nothing to narrow with, leads
  to asking for the full deal name or the account instead of a partial list. The step 2 result is
  kept only when it is the chosen deal; otherwise the full read reruns by Id.
- **Stage order (same gap as [#24](https://github.com/salesforce/salesforce-skills/issues/24); [follow-up comment](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032)).**
  The step 1 request adds the aliased `stages` root used by `deal-advance-gap`. The stage tile
  takes the deal's two-digit position and the stages left through Closed Won from it.

The mechanical comparison is 17 additions and 2 deletions: 940 source lines and 955 active lines.
Ten deterministic tests cover an exact source-plus-changes reproduction, upstream widget-block
parity, both source gaps, the materialized step 2, candidate, and grounding reads, the rule and its
branch order, the narrowing threshold against the candidate page size, and the stage-tile rule.
Static validation, widget parity, the offline widget contract, and the documented reads (4/4)
pass. On the synthetic org, the source read returned another rep's $21K deal for the last two words
of the requested deal's name and a different deal on the same account for the account name.
Walked through the corrected rule with live reads, seven lookups each ended correctly within four
reads. Those two phrases reported 78 and 14 matches and, narrowed with the account and the deal's
other words, returned 2 candidates, with the requested deal the one exact match. A request without
the full name took the one open candidate, a request naming no account asked for it instead of
listing 10 of 78, and a name three deals share, two of them open, led to asking which. The
corrected step 1 returned the org's ten stages in order, giving position 04 and five stages to
close. A second non-production org reproduced the issue's minimum setup directly and through the
Headless 360 `dispatch_readonly` tool: the source read returned the later-closing of two deals
that share a phrase, and the corrected reads listed both. Neither correction has been run in Quick
yet.

### `deal-signals`

The active mirror adds four rule paragraphs and changes no query, renderer JSON, or variable
contract:

- **Output choice ([#25](https://github.com/salesforce/salesforce-skills/issues/25)).** The widget is a single-opportunity buying-signal view
  whose composite score and six-week trend no step computes. A book or team sweep returns the
  step 5 digest instead of calling `display_widget`. For one named deal, the widget is rendered
  without its chart-and-meter `tile/column`, because the widget schema requires data for both
  tiles. Risk rows use Watch, `subtitle` gives signal counts only, and the "two graphs present"
  check is skipped.
- **Stale commitment (Quick/Kiro adaptation).** The signal fires when a next step is set and
  `LastModifiedDate` is 21 or more days old, since no field has changed since then; a more recent
  `LastModifiedDate` does not show the trigger.
- **Email evidence (Quick/Kiro adaptation).** When an email tool is available, the 2b email search
  runs; otherwise the output says email was not checked.
- **Complete digest (Quick/Kiro adaptation).** Every deal that fired a signal is listed under its
  strongest signal, lower-priority deals may share a line, and the digest always ends with the ✅
  line, checked against the number of flagged deals before sending.

The mechanical comparison is 8 additions and 0 deletions: 538 source lines and 546 active lines.
Fourteen deterministic tests cover an exact source-plus-changes reproduction, upstream widget-block
parity, rule placement and wording, and the widget schema: dropping only the chart and meter keys
leaves both tiles missing required attributes, while removing their column leaves a complete
single-deal widget. Static validation, widget parity, the offline widget contract, and the
documented reads pass. The hosted `display_widget` tool accepted the single-deal widget. A Quick
rerun of the book sweep returned the text digest, applied the stale-commitment rule, and said email
was not checked; it also dropped three flagged deals from the digest, which led to the
complete-digest rule. The next rerun listed all 21 flagged deals and ended with the ✅ line.

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
| E2E | 157/157; guards 6/6 |
| Widget parity | 26/26 |
| Hosted contracts | 26/26 |
| Ravelin browser | 26/26 with 130/130 semantic checks and 59/59 capture-only actions (39 messages, 20 links) |

Quick is unverified for package-wide behavior. Synthetic `calendar-events` and `customer-health` runs executed Headless 360 reads and rendered widgets successfully; after the local canonical-query safeguard, the health rerun needed no template retry. These runs do not establish installation, routing, rendering, email, or connector behavior for the remaining skills.
