# Quick/Kiro Skill Change Report

## Purpose

This is the living record of changes made specifically for reliable Salesforce skill execution in
Amazon Quick and Kiro. It records the observed host behavior, why the upstream behavior is being
preserved or changed locally, the narrow fix, and the evidence required to promote an experiment
into a maintained divergence.

The governing workflow is [`quick-kiro-skill-adaptation.sop.md`](quick-kiro-skill-adaptation.sop.md).
The core policy is:

- Report or change upstream only for a demonstrated, host-independent defect.
- Keep host-specific execution guidance in the local `agent-plugin/skills/` copy.
- Preserve upstream data access, consent, grounding, and output semantics.
- Prefer a text-only adaptation first when it can be tested without changing a query or renderer.
- Never represent missing, inaccessible, null, or unqueried data as a real value.

## Status summary

| Skill or component | Problem | Local fix | Status | Upstream impact |
|---|---|---|---|---|
| `account-context` | Quick reconstructed a long GraphQL template, lost brace structure, and moved `aggregate` under `query`. | Added canonical-query substitution and one-rebuild guidance. | **Quick validated** | None; source query remains unchanged. |
| `account-tiering` | Three visual bands disagreed with the binary `>=6` tier threshold. | Require a raw-score-based binary 2×2 heatmap and deterministic count reconciliation. | **Quick validated** | None; source scoring and renderer JSON remain unchanged. |
| `account-tiering` | Quick populated unavailable ARR and Whitespace values as `$0.00`. | Require grounded queried currency values; otherwise omit the keys and columns, never default to zero. | **Quick validated** | None; source query and renderer JSON remain unchanged. |
| `calendar-events` | The source query cannot ground deal output, and its subtitle claims an unsupported attendee count. | Query typed Opportunity facts and omit the attendee metric from the active subtitle. | **Quick validated** | [#20](https://github.com/salesforce/salesforce-skills/issues/20); active mirror temporarily diverges. |
| `customer-health` | Quick reconstructed the deep Account request, hit a syntax error, then recovered only after returning to the literal template. | Preserve the canonical `queryInput`, validate it before the first dispatch, and rebuild once from the standard-field literal on syntax failure. | **Quick validated** | None; source query is valid and unchanged. |
| `customer-health` | Support counts came from the ten most recent Cases (10 shown versus 118 in the window). | Add aggregate case totals to the same deep read; describe the rows only as the latest ten. | **Quick validated** | [#21](https://github.com/salesforce/salesforce-skills/issues/21); active mirror temporarily diverges. |
| `customer-health` | Quick's first `display_widget` call sent the widget as a JSON string; the tool rejected it and the retry rendered. | Show `account-context`'s object-not-string `widgetDefinition` example at the widget call. | **Local test passed; 1 clean Quick run, more required** | None; upstream already instructs object payloads. |
| `customer-voice` | With no quotes in docs or email, Quick searched Salesforce Tasks/Events the skill does not document, beyond the scoped accounts, and reported a page-capped count. | Take quotes only from docs and email with no extra Salesforce reads; keep a zero-quote result on the output template with the period and at most one in-skill next step. | **Quick validated** | None; the source already limits Salesforce to scoping reads. |
| `daily-briefing` | Quick rewrote row names to avoid repeating the account and gave one past-due row a name no record has; the row's other fields matched the real deal. | Copy row names from the returned values, using the Opportunity Name unchanged when it already begins with the Account Name. | **Quick validated** | None; the source asks for names from the response. |
| `daily-briefing` | No documented read maps an Opportunity-linked meeting to its Account; with no attendee domains, the source reads report such meetings as having no CRM match. | Select Event `AccountId` in the calendar read and pass those Ids to the meeting-account read. | **Quick validated** | [#22](https://github.com/salesforce/salesforce-skills/issues/22); active mirror temporarily diverges. |
| `daily-briefing` | Quick skipped the inbox and "you owe them" email checks without saying so, dropped the follow-ups section, and reused the follow-ups stat for stale deals. | When an email tool is available, run both checks and report the result in the follow-ups stat and inbox block; otherwise say the inbox was not checked. | **Quick validated for the inbox read** | None; the source already requires the inbox read. |
| `deal-advance-gap` | The step 2a name lookup returned 10 old closed deals for a two-word phrase and omitted the requested open deal; Quick found it only with its own extra search. | Search open deals only, select `totalCount`, and narrow once when the candidate list is cut off. | **Quick validated** | [#23](https://github.com/salesforce/salesforce-skills/issues/23); active mirror temporarily diverges. |
| `deal-advance-gap` | The default target is the next stage, but no documented read returns the stage order; two Quick runs named different targets, one wrong for the org. | Return the Stage picklist in the org's order in the step 1 request and take the default target from it. | **Quick validated** | [#24](https://github.com/salesforce/salesforce-skills/issues/24); active mirror temporarily diverges. |
| `deal-advance-gap` | Two Quick runs marked steps Scheduled or In motion with no open or future-dated task or event behind them. | Rest every Done, In motion, or Scheduled state on a returned task or event, with a widget self-check that downgrades any In motion or Scheduled row that cannot name its task or event. | **Quick validated** | None; the source already defines these states. |
| `deal-advance-gap` | Two Quick runs scored different generic lists as the org's exit criteria (1 of 6, then 0 of 5). | Unless the user names exit criteria, present the checklist as suggested steps based on the deal's data, without asking. | **Quick validated** | None; replaces the source's ask-once option locally. |
| `deal-review` | The step 2 read takes the latest-closing match for 1–2 words with `first: 1` and no count. A Quick run reviewed the right deal, but run as written in the synthetic org, the last two words of that deal's name returned another rep's $21K deal and the account name returned a different deal on the same account. | Select `totalCount`; when several deals match, run a documented candidate read, narrowed first by words from the request when more than 10 match, and take the one exact name match or the one open candidate, else ask without offering a cut-off list; rerun by Id when the chosen deal differs. | **Local tests and live reads pass; not yet run in Quick** | [#26](https://github.com/salesforce/salesforce-skills/issues/26); active mirror temporarily diverges. |
| `deal-review` | The stage tile needs the deal's stage position and stages left to close, but no `deal-review` read returns the stage order, the gap behind #24. The Quick run showed "04", correct only because the org uses the default stages, and "mid-funnel" instead of the stages left. | Return the Stage picklist in the org's order in the step 1 request, as in `deal-advance-gap`, and take the stage tile from it. | **Local tests and live reads pass; not yet run in Quick** | [Follow-up comment](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032) on [#24](https://github.com/salesforce/salesforce-skills/issues/24); active mirror temporarily diverges. |
| `deal-signals` | The widget is a single-deal buying-signal view whose composite score and six-week trend no step computes; Quick returned the text digest for a 21-deal book instead. | Return the step 5 digest for book and team sweeps; for one named deal, drop the chart-and-meter column from the widget. | **Book-sweep path Quick validated; single-deal widget not yet run in Quick** | [#25](https://github.com/salesforce/salesforce-skills/issues/25); active mirror temporarily diverges. |
| `deal-signals` | Every deal was last modified 39 days earlier, so no next step had changed in 21+ days, yet Quick flagged no stale commitment and called one deal clean. | Fire Stale commitment when a next step is set and `LastModifiedDate` is 21 or more days old. | **Quick validated after the complete-digest rule** | None; the source already lists the signal and fetches the field. |
| `deal-signals` | Quick ran no email search for the flagged accounts and did not say so, leaving the email-based signals implied clear. | When an email tool is available, run the 2b email search; otherwise say email was not checked. | **Quick validated** | None; the source already requires the evidence search when tools are present. |
| `deal-signals` | A rerun computed a signal for all 21 deals but listed 18 to keep the digest short, dropping the one deal whose only signal was a stale next step, and omitted the ✅ line. | List every flagged deal under its strongest signal, grouping lower-priority deals if needed, and always end with the ✅ line. | **Quick validated** | None; the source already lists each fired signal. |
| Configure E2E coverage | The exact-call runner silently omitted one documented UI API layout GET. | Added extraction, a narrow read-only adapter allowlist, static validation, and regression tests. | **Validated** | No skill behavior change. |
| Adaptation governance | The mirror policy previously assumed all local differences required upstream issues. | Added a host-adaptation SOP separating universal defects from Quick/Kiro divergences. | **Validated** | No upstream change. |

## Skill changes

### 1. `account-context`: preserve the canonical deep query

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

Quick successfully resolved the account and grounded metadata, then reconstructed the supplied
long GraphQL deep read. It produced unbalanced braces, attempted several manual repairs, and at
one point placed `aggregate` inside `uiapi.query`. The literal source query is valid and succeeds
when used as written, with `query` and `aggregate` as siblings under `uiapi`.

**Reason for a local change**

The failure was caused by host-side query construction, not by an invalid Salesforce query or API
contract. The upstream Claude/Cowork skill already works in its intended environment, so this is
not an upstream defect.

**Fix**

The active [`account-context` skill](../agent-plugin/skills/account-context/SKILL.md) now instructs
Quick/Kiro to:

1. Treat the supplied `queryInput` as a canonical request, not an outline.
2. Substitute only `<ID>`, `<ACCT_CUSTOM>`, `<OPP_CUSTOM>`, `<CONTACT_CUSTOM>`, and
   `<TASK_CUSTOM>`.
3. Insert only complete, metadata-confirmed custom-field selections.
4. Preserve `uiapi { query { ... } aggregate { ... } }` without moving or rewriting blocks.
5. On a syntax error, discard the generated request and rebuild once from the canonical template
   with all optional custom fields omitted instead of hand-repairing the failed query.
6. Stop and report the error if the canonical standard-field form fails.

**Validation**

- Static query validation passed.
- All seven documented `account-context` reads passed through the local read-only adapter.
- Widget contract parity and offline hydration passed because the query and renderer were not
  changed.
- A fresh Quick run completed the six expected Salesforce workflow reads without a brace-repair
  loop and visibly rendered the populated account widget.

**Files**

- `agent-plugin/skills/account-context/SKILL.md`

### 2. `account-tiering`: reconcile tier and heatmap thresholds

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

The skill assigns tiers from raw Fit and Engagement scores on a 0–10 scale, where `>=6` is high.
Quick correctly computed one Tier A account and ten Tier B accounts, but rendered a three-band
heatmap using High `7–10`, Mid `4–6`, and Low `0–3`. As a result:

- the raw `10/6` Tier A account appeared in the Mid-engagement column;
- raw Fit `7` accounts could appear in a Mid-fit row despite being high-fit for tiering; and
- the heatmap could show an empty High/High cell while the pie chart showed a nonzero Tier A.

**Reason for a local change**

The source tier logic is correct. The host introduced a separate three-band visualization mapping
that did not share the tier boundary. The first local experiment therefore clarifies how Quick/Kiro
must hydrate the existing widget without changing Salesforce reads or the upstream renderer JSON.

**Fix**

The active [`account-tiering` skill](../agent-plugin/skills/account-tiering/SKILL.md) now requires:

- `heatmapXLabels`: `Low (0–5)`, `High (6–10)`;
- `heatmapYLabels`: `High fit (6–10)`, `Low fit (0–5)`;
- cell assignment from raw scores before display conversion;
- High/High = Tier A, High/Low = Tier B, Low/High = Tier C, Low/Low = Deprioritize;
- the heatmap-cell total, pie-slice total, and scored-book count to agree; and
- no Mid-fit or Mid-engagement band.

The Tier A table may continue to display Fit as `raw Fit / 2` and Engagement as
`raw Engagement * 10`, but those presentation values cannot determine tier or heatmap placement.

**Validation**

- A deterministic test verifies the boundary cases and the `1 / 10 / 0 / 0` reconciliation.
- All three documented `account-tiering` Salesforce reads passed.
- Widget JSON parity and offline hydration passed because this experiment changes instructions,
  not the renderer template.
- The Quick rerun visibly rendered a binary 2×2 heatmap with one Tier A in High/High and ten Tier B
  accounts in High-fit/Low-engagement. The heatmap, pie, subtitle, and total all reconciled to 11.

**Files**

- `agent-plugin/skills/account-tiering/SKILL.md`
- `agent-plugin/evals/test_account_tiering_reconciliation.py`

### 3. `account-tiering`: do not fabricate optional ARR or Whitespace

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

A diagnostic metadata grounding pass found no accessible Account currency field explicitly
representing ARR and no currency field representing Whitespace or Expansion Potential. Standard
Annual Revenue is not ARR, and an upsell-status picklist is not a monetary whitespace value.
Quick nevertheless inserted numeric zeroes for both metrics, causing the widget to display
`$0.00` as though Salesforce had returned real values.

**Reason for a local change**

The Salesforce read and tier scores were valid; the host filled required-looking widget row keys
with defaults. This violates the shared no-fabrication rule. The local instruction must make the
optional nature of these two widget metrics explicit.

**Fix**

The active `account-tiering` skill now requires:

- `arr` only from an accessible, grounded currency field explicitly representing ARR or Annual
  Recurring Revenue and actually queried in the account read;
- `white` only from an accessible, grounded currency field explicitly representing a monetary
  Whitespace or Expansion Potential value and actually queried;
- no substitution of standard Annual Revenue for ARR;
- no conversion of a picklist or qualitative upsell signal into a currency amount;
- omission of the unavailable row key and its datagrid column; and
- no use of `0`, `$0`, or `$0.00` as a missing-data placeholder.

If both metrics are unavailable, the Tier A table should contain only Account, ICP fit,
Engagement, and Motion.

**Validation**

- The deterministic local test checks that the active instruction contains the grounding,
  omission, and no-zero requirements.
- Static validation, the three Salesforce reads, widget parity, and offline hydration pass.
- A normal Quick rerun visibly omitted both ARR and Whitespace columns rather than rendering
  `$0.00`. The resulting Tier A table contains only Account, ICP fit, Engagement, and Motion.
- The same run preserved the previously validated binary heatmap reconciliation: one Tier A in
  High/High, ten Tier B in High-fit/Low-engagement, and 11 accounts total.

**Files**

- `agent-plugin/skills/account-tiering/SKILL.md`
- `agent-plugin/evals/test_account_tiering_reconciliation.py`

### 4. `customer-health`: preserve the canonical deep query before dispatch

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

Quick reconstructed the deep Account read, sent a malformed request, and reported a syntax error.
It then returned to the literal template, validated brace balance, and completed the health widget.
The source and active query were identical and structurally valid; the failure occurred before the
successful canonical replay.

**Fix**

The active `customer-health` skill now requires Quick/Kiro to:

1. copy the complete canonical `queryInput` as one unit;
2. substitute only `%ACCOUNT%`, `<ACCT_CUSTOM>`, or the documented complete exact-Id filter;
3. decode the nested JSON and validate placeholders and bracket balance before the first dispatch;
4. never send a reconstructed request merely to let Salesforce discover syntax errors; and
5. on a syntax failure, discard the request and rebuild once from the literal standard-field
   template with `<ACCT_CUSTOM>` omitted, then stop if that still fails.

**Validation**

- Three deterministic tests verify the local instruction, standard-field materialization, and
  exact-Id recovery form.
- Static validation and documented-call extraction pass; the source query remains unchanged.
- The complete local Python suite passes 17/17.
- A fresh Quick rerun of the same prompt completed its Salesforce reads on the first attempt—no
  syntax error, rebuild, or brace check—and rendered the populated health widget in 7 steps
  instead of 9.

**Files**

- `agent-plugin/skills/customer-health/SKILL.md`
- `agent-plugin/evals/test_customer_health_query_integrity.py`

### 5. `customer-voice`: keep zero-quote results within the skill's sources

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

A synthetic Quick run found no transcripts and no customer email on the topic. It then searched
Salesforce Tasks/Events, which the skill does not document; the skill uses Salesforce only to
scope accounts and identify internal speakers. That search was not limited to the scoped
accounts. The output cited a deal on another rep's account and reported 200 activities. A
read-only check found 87 activities (65 Tasks, 22 Events) on the scoped accounts' generator deals
and 273 org-wide. The 0-quote conclusion was correct because every scoped activity note was
placeholder text. The output also omitted the period and closed with a menu that offered Slack,
which is not a customer-voice source. The documented reads pass in the exact-call runner, so the
source works as written.

**Fix**

The active `customer-voice` skill now:

1. takes quotes only from the docs and email searches;
2. makes no Salesforce reads beyond the three scoping reads, uses no Task, Event, Case, or other
   record search as a substitute source, and reports no counts from one; and
3. when no quote is found, keeps the output template with 0 quotes, the topic, and the period,
   writes `None` under Accounts represented, fills Gaps, and offers at most one next step: a wider
   period or scope, or a transcript, notes doc, or email thread to search.

**Validation**

- Four deterministic tests check rule placement and wording and the three documented scoping
  reads. They also confirm that removing the two rules restores the source byte-for-byte.
- Static validation and the exact-call runner pass (4/4 calls); the queries and output template
  are unchanged.
- The eval rubric adds the source and zero-quote expectations.
- A normal Quick rerun of the same prompt returned the template header with 0 quotes and the
  30-day period, `None` under Accounts represented, and Gaps for the scoped accounts. Its step
  list showed no Salesforce search after the scoping reads, and the output reported no activity
  counts. The closing line and follow-up suggestions offered only a wider period, one account, or
  a user-provided source. The run took 11 steps instead of 13, with no failed call. The individual
  host calls and the email and docs results were not visible for independent verification.

**Files**

- `agent-plugin/skills/customer-voice/SKILL.md`
- `agent-plugin/evals/test_customer_voice_sources.py`
- `agent-plugin/evals/skills/customer-voice/eval.yaml`

### 6. `daily-briefing`: copy row names from returned values

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

A synthetic Quick briefing for a named date rendered 13 closing-soon and past-due rows. In this
org every Opportunity Name already begins with its Account Name, so the source's
`<Account> — <Opp Name>` format would repeat the account. Quick rewrote the names instead, and one
past-due row received a name that no record has; its stage, close date, amount, and next step
matched the real deal. The other values in the widget matched read-only checks.

**Fix**

The active skill now copies each `closingRows` and `pastDueRows` name from the returned values.
It uses the Opportunity Name unchanged when it already begins with the Account Name, otherwise the
source format, and never retypes, shortens, or rewords a name.

**Validation**

- Two deterministic tests check the rule's placement and wording. An exact-delta test confirms
  that the source plus this rule, the inbox-check rule, and the meeting-account correction
  reproduces the active skill byte-for-byte.
- Static validation, widget parity, the offline widget contract, and the documented reads (7/7)
  pass; the rule changes no query or renderer JSON.
- The eval rubric adds the row-name expectation.
- Two Quick reruns of the same prompt rendered all 13 row names exactly as stored.

**Files**

- `agent-plugin/skills/daily-briefing/SKILL.md`
- `agent-plugin/evals/test_daily_briefing_local_changes.py`
- `agent-plugin/evals/skills/daily-briefing/eval.yaml`

### 7. `daily-briefing`: report the inbox check instead of dropping it

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

A synthetic Quick rerun made six Salesforce reads and one widget call, but no email call, although
the previous run used the email tool and reported no unread customer mail. The widget had no
follow-ups or inbox section and used the follow-ups stat for stale deals instead, so nothing told
the user that the inbox had not been checked. The source already lists the inbox read as one of
the briefing's batched reads.

**Fix**

When an email tool is available, the active skill now runs the inbox read and step 3's "you owe
them" search as part of the briefing. It reports their result in the follow-ups stat and the
owe/inbox block, or the Inbox section in the text fallback, using `inboxClear` when nothing is
found. If no email tool is available or the search fails, it keeps that stat and block and says
the inbox was not checked.

**Validation**

- Two deterministic tests check the rule's placement and wording and confirm that the widget
  tokens it names exist. The exact-delta test covers it with the other daily-briefing changes.
- Static validation, widget parity, the offline widget contract, and the documented reads (7/7)
  pass; the rule changes no query or renderer JSON.
- The eval rubric adds the inbox expectation.
- A Quick rerun accessed email and showed the follow-ups stat and an inbox-clear section. Its step
  list does not show whether the "you owe them" search ran, and the section mentions only unread
  mail.

**Files**

- `agent-plugin/skills/daily-briefing/SKILL.md`
- `agent-plugin/evals/test_daily_briefing_local_changes.py`
- `agent-plugin/evals/skills/daily-briefing/eval.yaml`

### 8. `deal-advance-gap`: rest row states on returned activity

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

In two synthetic Quick runs on the same deal, the widget showed a step as Scheduled or In motion
with nothing behind it. The first run marked an undated next step "On track / Scheduled"; the deal
had no events and every task was completed. The second marked "value case accepted" In motion on
the strength of a completed proposal task. The source already defines In motion as an open task or
a future-dated task or event.

**Fix**

Every Done, In motion, or Scheduled state now rests on 2b's Tasks and Events. Done needs a
completed task or a past-dated event; In motion or Scheduled needs an open task or a future-dated
task or event for that step. A step held only as Next Step text, or a completed touch still
awaiting a reply, is Not started.

**Validation**

- Two deterministic tests check the rule's wording and its placement in the gap-mapping step; the
  exact-delta test covers it with the other deal-advance-gap changes.
- The eval rubric adds the state expectation.
- A Quick rerun applied the states correctly to four rows but still marked a step In motion on the
  strength of a completed proposal with no reply, the exact case the rule names. Because the text
  rule alone did not hold, the widget self-verification list now also requires every In motion or
  Scheduled row to name its open or future-dated task or event in the row text, or be set to Not
  started. A third deterministic test covers that check.
- The next Quick rerun marked all five open rows Not started, including a next step held only as
  text, and backed its one Done row with the completed proposal task. That matches the record,
  which has no open or future-dated tasks or events. Because the deal had no open activity, the
  run did not test whether a supported In motion row still appears.

### 9. `deal-advance-gap`: label unsourced exit criteria as suggested steps

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

The two runs scored the deal against different generic sales criteria as if they were the org's
exit criteria: "1 of 6" in the first and "0 of 5" in the second. The documented reads do not return
exit criteria, and the source's alternative is to ask the user once.

**Fix**

Unless the user names exit criteria, the checklist is presented as suggested steps based on the
deal's returned data, without asking. The output says "suggested steps" wherever it would say exit
criteria, including `headerSubtitle` and `meterValueLabel`, and the callout says these are not the
org's defined criteria. The renderer's fixed "Exit criteria met" meter label is unchanged.

**Validation**

- Two deterministic tests check the rule's wording, its placement, and that the widget tokens it
  names exist. The eval rubric adds the expectation.
- Two Quick reruns labeled the meter line, the grid caption, and the callout as suggested steps
  rather than the org's exit criteria, without asking. Both also retitled the meter itself, which
  the rule does not require; the result was consistent.

**Files for sections 8 and 9 and the stage-order correction**

- `agent-plugin/skills/deal-advance-gap/SKILL.md`
- `agent-plugin/evals/test_deal_advance_gap_local_changes.py`
- `agent-plugin/evals/skills/deal-advance-gap/eval.yaml`

### 10. `deal-signals`: flag stale next steps from the last-modified date

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

A synthetic Quick sweep of 21 open deals flagged no stale commitment. Every deal had been last
modified 39 days earlier, so none of the 18 next steps could have changed in 21 days, and the skill
already fetches `LastModifiedDate` for its thresholds. Quick called one deal clean on that basis.

**Fix**

Stale commitment fires when a next step is set and `LastModifiedDate` is 21 or more days before
today, because no field on the deal has changed since then. A more recent `LastModifiedDate` does
not show the trigger, so the signal does not fire.

**Validation**

- Two deterministic tests check the rule's placement and wording and that the step 2 read still
  selects `LastModifiedDate`. The eval rubric adds the expectation.
- Applied to the same synthetic book, the rule flags all 18 deals with next steps, including the
  one the run called clean.
- A Quick rerun applied the rule in its reasoning and showed one deal's next step as unchanged
  since its last edit. Its digest then listed 18 of the 21 flagged deals and dropped three without
  saying so, including the deal whose only signal is a stale next step.
- After the section 12 rule, the next rerun listed that deal under Stale commitment and noted that
  nearly every next step in the book had not moved since the same date.

### 11. `deal-signals`: say when the email evidence was not checked

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

The same sweep made only its two Salesforce reads and no email search, although earlier runs in
that environment used the email tool. Inbound-waiting, champion-risk, and competitor signals depend
on that evidence, and the digest gave no sign they were unchecked.

**Fix**

When an email tool is available, the 2b email search runs for the flagged accounts as part of the
sweep. If no email tool is available or the search fails, the output says email was not checked,
under the ✅ line in the digest or in the widget callout.

**Validation**

- Two deterministic tests check the rule's placement and wording. The eval rubric adds the
  expectation.
- A Quick rerun without an email connector ended its digest by saying email, Slack, and docs were
  not checked, so the inbound-waiting, champion-risk, and competitor signals were not reflected.

### 12. `deal-signals`: list every flagged deal

**Classification:** Local Quick/Kiro adaptation.

**Observed behavior before the change**

A Quick rerun of the 21-deal sweep computed a signal for every deal, then, by its own reasoning,
listed 18 to keep the digest short. It dropped two smaller quiet deals and the one deal whose only
signal was a 39-day-old next step, omitted the ✅ line, and gave no sign anything was left out. The
source format lists each fired signal and ends with that line.

**Fix**

Every deal that fired a signal is listed under its strongest signal. Lower-priority deals in the
same group may share a line, but no flagged deal is dropped to shorten the digest, and the digest
always ends with the ✅ line. Before sending, the number of deals listed must equal the number
that fired a signal.

**Validation**

- Two deterministic tests check the rule's placement after the digest template and its wording;
  the exact-delta test covers it with the other deal-signals changes. The eval rubric adds the
  expectation.
- A Quick rerun listed all 21 flagged deals in three groups with counts (11, 1, and 9) and ended
  with the ✅ line, matching the 21 open deals on the rep's accounts.

**Files for sections 10 to 12 and the output-choice correction**

- `agent-plugin/skills/deal-signals/SKILL.md`
- `agent-plugin/evals/test_deal_signals_local_changes.py`
- `agent-plugin/evals/skills/deal-signals/eval.yaml`

## Supporting validation changes

### Configure UI API layout read coverage

The exact-call E2E runner previously recognized only GraphQL calls with `queryInput` and SOQL
calls with `q`. It silently omitted Configure's documented read-only call:

```text
GET /services/data/v63.0/ui-api/records/<OPP_ID>
layoutTypes=Full&modes=View
```

The local test adapter also permitted only GraphQL and SOQL endpoints.

**Fix**

- Extract the layout call as a first-class `layout` read.
- Obtain an accessible Opportunity Id from Configure's documented preceding lookup.
- Permit only API `v63.0`, an Opportunity (`006`) Id, and exactly `layoutTypes=Full` plus
  `modes=View`.
- Reject wrong versions, non-Opportunity IDs, extra path segments, incorrect modes/layout types,
  extra parameters, non-GET methods, and every other UI API route before Salesforce is contacted.
- Validate each complete `dispatch_readonly(...)` expression so a later query cannot accidentally
  satisfy an earlier unsupported call.

**Validation**

- Full exact-call baseline: **156/156** reads passed on a non-production Developer Edition target.
- Safety guards: **6/6** passed.
- Offline extraction, adapter-policy, and static-validation regression tests passed.

**Files**

- `agent-plugin/evals/e2e_calls.py`
- `agent-plugin/evals/local-mcp/salesforce-readonly-mcp`
- `agent-plugin/evals/validate.py`
- `agent-plugin/evals/test_e2e_calls.py`
- `agent-plugin/evals/test_salesforce_readonly_mcp.py`
- `agent-plugin/evals/test_validate_layout_read.py`
- supporting baseline documentation under `agent-plugin/` and `docs/`

## Investigated items with no skill change

| Item | Decision | Reason |
|---|---|---|
| Missing `display_widget` in Quick | Connector configuration, not a skill defect | Loading `using-display-widget` cannot expose an MCP tool. Once the connector exposed `display_widget`, Quick rendered successfully. |
| `draft-outreach` missing-email fallback | No change | Quick already pauses honestly, offers connection or copyable text, and does not claim delivery. Additional skill wording would duplicate host behavior. |
| `inbox-sweep` missing-email fallback | No change | Same as `draft-outreach`; no observed consent or delivery failure. |
| `team-pipeline` large-result wording | No change yet | No reproduced Quick/Kiro failure requiring different behavior has been established. |
| `voice-profile` connection wording | No change yet | No demonstrated outcome failure or universally incorrect source behavior has been established. |
| `account-tiering` Salesforce query | No change | Quick successfully executed the documented metadata and account-book reads; the defect was in model-authored display mapping. |

## Submitted upstream issue and active divergence

[`#20`](https://github.com/salesforce/salesforce-skills/issues/20) records two host-independent
`calendar-events` source defects. The active Quick/Kiro copy now carries the narrow local
correction while the upstream source remains unchanged.

| Skill | Reproduced defects | Local correction | Validation | Upstream impact |
|---|---|---|---|---|
| `calendar-events` | `What` omitted runtime type, related ID, and Opportunity facts required by deal-linked/Value output; `Who` could not establish an attendee count. | Add typed Opportunity `What` fields, ground deal output only from those returned values, and omit the attendee metric from the subtitle. | Static query validation, documented-call extraction, renderer parity, offline hydration, browser-input checks, and a successful synthetic Quick widget run pass. | [#20](https://github.com/salesforce/salesforce-skills/issues/20) remains open; source is unchanged. |

## Submitted upstream issues with local corrections

[`#21`](https://github.com/salesforce/salesforce-skills/issues/21),
[`#22`](https://github.com/salesforce/salesforce-skills/issues/22),
[`#23`](https://github.com/salesforce/salesforce-skills/issues/23),
[`#24`](https://github.com/salesforce/salesforce-skills/issues/24),
[`#25`](https://github.com/salesforce/salesforce-skills/issues/25), and
[`#26`](https://github.com/salesforce/salesforce-skills/issues/26) record these host-independent
defects, and a [follow-up comment](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032)
on #24 adds the same stage-order gap in `deal-review`. The active copy carries each correction
while the upstream source remains unchanged.

| Skill | Reproduced defect | Local correction | Validation | Local record |
|---|---|---|---|---|
| `customer-health` | `Cases(first: 10)` capped the Support signal: a synthetic account with 118 Cases in the window rendered as 10 cases with 1 escalated. | Add `matchedAccounts`, `caseTotal`, `caseOpen`, `caseEscalated`, and `caseHighPriority` aggregates to the same request; take Support counts from them and rerun by Id when the name matches several accounts. | Seven deterministic tests, exact-call execution, and live name and exact-Id reads matching an independent count. A Quick rerun rendered Support as 118 cases with 89 High/Critical, 13 open, and 3 escalated, matching that count. | [`customer-health-capped-case-counts.md`](issues/customer-health-capped-case-counts.md) |
| `daily-briefing` | Two Opportunity-linked meetings with no attendee domains left the meeting-account read with no Account Id or domain to match, so the source reads report them as having no CRM match. In the Quick run, the meeting card showed a field no documented read selects, so the host went outside the skill's reads, and the card still omitted the account's second open deal. | Select Event `AccountId` in the calendar read and pass those Ids to the meeting-account read; keep the domain match as the fallback. | Five deterministic tests cover the source gap, the Event selection, the meeting-account read, the instructions, and an exact source-plus-changes check. The documented reads pass 7/7. On the synthetic org, the corrected reads resolved both meetings to their Account and its two open Opportunities for both the current and the next day. A second non-production org reproduced the draft from its own minimum setup through the Headless 360 `dispatch_readonly` tool: the source reads returned only the Opportunity link, the Event `AccountId` resolved the Account and both open Opportunities, and the `WhatId` alone matched no Account. Two Quick reruns' meeting cards listed both open deals on the account, used only fields the documented reads return, and prompted the rep to raise the past-due deal in the meeting. | [`daily-briefing-meeting-account-link.md`](issues/daily-briefing-meeting-account-link.md) |
| `deal-advance-gap` | The step 2a lookup matches 1–2 words, sorts by close date ascending, and returns 10 rows with closed deals included and no total. A two-word phrase matched 78 deals (19 open); the first 10 were all closed and omitted the requested open deal. Followed as written, the skill would ask the user to choose among them. | Search open deals only, select `totalCount`, narrow the search once when the total exceeds the rows returned, and include the account name when the request gives one. | Four deterministic tests cover an exact source-plus-changes check, the source gap, the materialized candidate read, and the branch order; the documented reads pass 5/5. On the synthetic org, the corrected lookup reported 19 open matches for 10 rows, and adding the account name returned only the requested deal. A second non-production org reproduced the draft's minimum setup through the Headless 360 `dispatch_readonly` tool: the source lookup returned 10 closed deals without the open one, and the corrected lookup returned the open deal alone. A Quick rerun reported the cut-off list (19 matches), narrowed by account, and resolved the deal on that one retry; it did not include the account in its first search, although the request named it. | [`deal-advance-gap-name-lookup.md`](issues/deal-advance-gap-name-lookup.md) |
| `deal-advance-gap` | The default target is "next stage", but the step 1 read returns `StageName` only as a label and no documented read returns the stage order. Two Quick runs on the same Value Proposition deal named the next stage "Identify Decision Makers" (the org's label is Id. Decision Makers) and then Proposal/Price Quote, three stages later. | Add an aliased `stages` root to the step 1 request that returns the Stage picklist in the org's order (master record type), and take the default target from it. | The exact-delta and grounding-read tests pass, and the documented reads pass 5/5 with the new step 1 call. On the synthetic org, the documented step 1 returned all ten stages in order with Id. Decision Makers after Value Proposition. In a second non-production org, the source step 1 returned no stage values through the Headless 360 `dispatch_readonly` tool, and the corrected request returned the ordered list. Two Quick reruns named Id. Decision Makers as the next stage. | [`deal-advance-gap-stage-order.md`](issues/deal-advance-gap-stage-order.md) |
| `deal-signals` | The skill sweeps the rep's whole book, but its required widget is a single-opportunity buying-signal view with a 0–100 composite score and a six-week score trend. No step defines the score or reads history, the rules forbid invented values, the pre-render check requires both graphs, and the widget schema requires data for both tiles. A Quick sweep of 21 deals returned the text digest without calling `display_widget`. | Return the step 5 digest for book and team sweeps; for one named deal, render the widget without its chart-and-meter column, with Watch on risk rows and signal counts in `subtitle`. | Fourteen deterministic tests, including an exact source-plus-changes check, upstream widget-block parity, and a schema check: dropping only the chart and meter keys leaves both tiles missing required attributes, while removing their column leaves a complete widget. The documented reads pass. Step 2 returned 21 deals in the synthetic org and 54 in a second non-production org through the Headless 360 `dispatch_readonly` tool, with no score or history fields. The hosted `display_widget` tool accepted the single-deal widget. A Quick rerun of the book sweep returned the text digest; the single-deal widget has not been run in Quick. | [`deal-signals-widget-contract.md`](issues/deal-signals-widget-contract.md) |
| `deal-review` | Step 2 matches 1–2 words, sorts by close date descending, and takes `first: 1`, with no count; its resolver runs only on an empty result. In the synthetic org, the last two words of the requested deal's name matched 78 deals and returned another rep's $21K deal, and the account name matched 14 and returned a different $836K deal on the same account. | Select `totalCount`; above 1, run the documented candidate read (`first: 10`), narrowed first by the account or other words from the request when more than 10 match. Take the one exact name match or the one open candidate, else ask, and never offer a cut-off list. Keep the step 2 result only when it is the chosen deal; otherwise rerun the full read by Id. | Ten deterministic tests, including an exact source-plus-changes check, and the documented reads pass 4/4. On the synthetic org, seven lookups walked through the corrected rule with live reads each ended correctly within four reads, including a request naming no account, which asked for it, and a name shared by two open deals, which asked which. A second non-production org reproduced the issue's minimum setup directly and through the Headless 360 `dispatch_readonly` tool. Not yet run in Quick. | [`deal-review-name-lookup.md`](issues/deal-review-name-lookup.md) |
| `deal-review` | The stage tile needs the deal's stage position and the stages left to close, but step 1 returns `StageName` only as a label and no read returns the stage order. | Add the aliased `stages` root from `deal-advance-gap` to the step 1 request and take `kpiStageNum` and `kpiStageSub` from it. | The exact-delta and grounding-read tests pass. On the synthetic org, the corrected step 1 returned the org's ten stages in order, giving position 04 and five stages to close. Not yet run in Quick. | [`deal-advance-gap-stage-order.md`](issues/deal-advance-gap-stage-order.md), follow-up comment |

## Open observations

- Quick has sometimes emitted progress narration despite skills requesting silent execution.
- Quick has sometimes added a prose recap after a successful terminal `display_widget` call. One
  `deal-advance-gap` recap attributed stage criteria to the customer account rather than the
  selling org; the widget itself had it right.
- Narration and recap are host presentation behaviors. They have not caused incorrect Salesforce
  data or unsafe actions, so no skill divergence is proposed for them.
- Quick once passed `widgetDefinition` to `display_widget` as a JSON string instead of an object
  (`customer-health`, one of three runs). The tool rejected it and the retry rendered correctly.
  The active skill now adds `account-context`'s WRONG/RIGHT payload example at the widget call.
  The first Quick run with it made a single successful widget call; because the failure was
  intermittent, more runs are needed before treating it as fixed. Extend it to other widget
  skills only if the failure recurs there.
- A `customer-health` run showed the standard Account Rating, which the canonical deep read does
  not select. Quick most likely placed it in the `<ACCT_CUSTOM>` slot, which the skill reserves
  for confirmed `__c` fields. The value matched the record and the request succeeded. Whether that
  run also selected the account's grounded health-score field is unverified. No change is proposed
  unless Quick skips grounded health fields or an added field causes a failure.
- The same briefing, requested for the next day, correctly used that date for meetings,
  countdowns, and past-due ages. It computed one last-touch age from the current date, which made
  it one day short. Its gap stat counted only blank next steps, although the skill also flags
  stale deals. Neither misstated a record value, so no change is proposed. A rerun measured every
  age from the briefing date and counted both stale deals.
- A later `daily-briefing` rerun labeled the second-largest past-due deal as the largest. It also
  reported one meeting where the calendar had two overlapping events for the same account; earlier
  runs showed both and flagged the double booking. The skill already requires output to match the
  queried values, and earlier runs got both right, so no rule is proposed unless either recurs.
- In three `deal-advance-gap` reruns, the first candidate search used only the deal words,
  although the requested deal name began with the account name. Each run then saw the cut-off list,
  narrowed once by account, and found the deal: one extra read, within the eval's four-read budget.
  The outcome is correct, so no further rule is proposed.
- A `deal-signals` digest matched the record for all 21 deals, but its added closing headline put
  the overdue total at $2.1M; the 11 listed overdue deals sum to $2,364,000. The digest format has
  no total line, so no rule is proposed unless it recurs. The same run's missing widget, stale
  commitments, and skipped email search are addressed by the deal-signals changes above.
- The next `deal-signals` rerun dropped three flagged deals from its digest, which section 12
  addresses. Smaller slips in the same run: one quiet group was labeled "last touch early Sep"
  although one of its deals was last touched Aug 19, a deal closing in two days was said to slip
  "tonight", and one deal link displayed as raw markdown. None misstated a record value, so no rule
  is proposed for them.
- The following `deal-signals` rerun listed all 21 deals but called Ostvold's $546K deal the
  "highest-value overdue"; Corvane's $674K overdue deal is larger. An earlier `daily-briefing` run
  gave Ostvold's deal the same wrong label, and an earlier `deal-signals` run misstated the overdue
  total, so ranking and total claims have now been wrong three times across two skills. A narrow
  rule is proposed for both skills but not applied: state a ranking or total only after checking it
  against the listed amounts, and otherwise leave it out. The same digest wrote "closed <date>" on
  each overdue row, although every one is still open.
- A `deal-review` run reviewed the right deal, matched the record, and showed its score math. Its
  lookup and stage-tile findings are addressed by the corrections above. It also left out
  the contact's recorded Decision Maker role and, like other runs, added a sentence after the
  widget. No rule is proposed for either unless the role omission recurs.
- If a text-only instruction is ignored in repeated host runs, prefer a narrow structural widget
  contract or deterministic adapter over adding more repetitive prose.

## Promotion criteria

An experimental change becomes a maintained Quick/Kiro divergence only after:

1. the original behavior is reproduced in Quick/Kiro with synthetic data;
2. the upstream source is shown to work as written or otherwise remains outside the defect;
3. the local change passes static and targeted deterministic tests;
4. the relevant Salesforce reads remain unchanged and valid unless the host evidence requires a
   query change;
5. a normal host run—without extra diagnostic prompting—demonstrates the intended result; and
6. `agent-plugin/CONVERSION_RECIPE.md` and `docs/portable-skill-diff-report.md` are updated with
   the approved local divergence before commit.

## Current release state

The changes in this report are currently local and uncommitted on the release branch. The
`account-context` canonical-query rule, `account-tiering` binary heatmap rule, `account-tiering`
optional-metric omission rule, `calendar-events` #20 correction, and `customer-health`
canonical-query safeguard are maintained local divergences. All five have been validated in normal
Quick runs. The newer customer-health case-total correction is also Quick-validated. Its
widget-payload example has one clean Quick run; more are needed because the original failure was
intermittent. The `customer-voice` source and zero-quote rules are Quick-validated in one normal
rerun. The `daily-briefing` row-name rule and meeting-account correction are Quick-validated in
two normal reruns, and its inbox-check rule in one; the meeting-account correction is filed
upstream as [#22](https://github.com/salesforce/salesforce-skills/issues/22). The
`deal-advance-gap` name-lookup correction is Quick-validated in one rerun and filed upstream as
[#23](https://github.com/salesforce/salesforce-skills/issues/23). Its stage-order correction,
suggested-step rule, and row-state rule with its render-time self-check are Quick-validated; the
stage-order correction is filed upstream as
[#24](https://github.com/salesforce/salesforce-skills/issues/24). In `deal-signals`, the
book-sweep output choice and the email-evidence, stale-commitment, and complete-digest rules are
Quick-validated. The single-deal widget has not been run in Quick, and the widget correction is
filed upstream as [#25](https://github.com/salesforce/salesforce-skills/issues/25). The
`deal-review` multiple-match and stage-order corrections pass local tests and live reads but have
not been run in Quick; the multiple-match correction is filed upstream as
[#26](https://github.com/salesforce/salesforce-skills/issues/26), and the stage-order gap is noted
in a [follow-up comment](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032)
on #24.
