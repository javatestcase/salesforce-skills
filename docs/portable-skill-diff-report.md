# Portable Skill Diff Report

## Scope and baseline

This compares each current upstream Claude/Cowork skill in `salesforce-for-sales/skills/` with its portable Agent Plugins counterpart in `agent-plugin/skills/`.

**Verdicts**
- **Portable output only** — Salesforce reads and analysis rules are preserved; required Cowork widget delivery becomes Markdown-first, with optional host-specific rich rendering.
- **Safety clarification** — no data-path change, but draft-only or user-applied-write behavior is made more explicit.
- **Material** — a Salesforce read, execution shape, or user-visible fallback changed.

## Cross-cutting changes

1. **Widget-first → Markdown-first.** Upstream skills generally require `display_widget` on Cowork when available, with text as fallback. Portable skills make Markdown the primary deliverable and move rich output to the optional `com.salesforce.quick/ui` extension. This changes presentation and removes Cowork-only `display_widget` dependencies; it does not, by itself, alter Salesforce analysis.
2. **Host-neutral Salesforce adapter.** Portable skills retain the documented `dispatch_readonly` URL/query contract but say a host such as Quick can use an equivalent configured read tool.
3. **Read-only posture is explicit.** Portable skills consistently state that Salesforce writes are not performed. Where applicable, proposed CRM changes are a checklist for the user rather than an action the skill performs.
4. **Optional connectors remain optional.** Email, docs, calendar, web, and Slack are still used where upstream used them. The portable skills do not disable them. A host without a connector skips optional evidence or uses a documented text fallback.

## Skill-by-skill comparison

| Skill | Verdict | What changed and why |
|---|---|---|
| `account-context` | Portable output only | Account resolution, four ObjectInfo grounding calls, account-by-ID read, aggregate, and optional email/docs/Slack enrichment are unchanged. Mandatory widget delivery became a Markdown account brief. The portable version explicitly notes unavailable optional sources rather than implying account silence. |
| `account-tiering` | Portable output only | Account/Opportunity/Contact reads, tier logic, and optional evidence sources are unchanged. Markdown tiers replace required Cowork widget delivery. |
| `calendar-events` | Portable output only | Current-user timezone and scoped Event reads, including polymorphic `Who`/`What` handling, are unchanged. Markdown schedule is primary; rich schedule is optional. |
| `call-follow-up` | Safety clarification | Salesforce grounding and account/opportunity-history reads are unchanged. Upstream already required an email draft and Slack draft; portable wording explicitly forbids sending or posting without user action, makes CRM changes a user-applied checklist, and retains copyable Slack text when draft creation is unavailable. |
| `call-prep` | Portable output only | Meeting resolution, account grounding, account/activity reads, and optional email/docs/Slack enrichment are unchanged. Markdown call brief replaces widget-first delivery. |
| `close-plan` | Safety clarification | Opportunity/contact-role reads and business-case/MAP logic are unchanged. Portable wording makes proposed CRM changes user-applied recommendations, not a host write action. |
| `customer-health` | Portable output only | Account, opportunity, case, and task reads plus optional email/calendar/docs/Slack evidence are unchanged. Output is Markdown-first. |
| `customer-voice` | Portable output only | Salesforce account scope, internal-speaker checks, and optional transcript/email evidence behavior are unchanged. Portable output is a Markdown digest instead of a required widget. |
| `daily-briefing` | **Material** | Retains the calendar, closing-soon, past-due, current-user, and meeting-context reads. Adds two Salesforce aggregate reads for closing-soon and past-due sections. Counts and amounts must now come from server aggregates, never from the bounded `first:50` detail rows; output discloses partial detail rows. **Why:** makes totals authoritative and avoids misleading totals from capped samples. |
| `deal-advance-gap` | Portable output only | Opportunity grounding, resolution, rich detail, and optional evidence reads are unchanged. The exit-criteria plan is Markdown-first. |
| `deal-review` | Safety clarification | Opportunity, contact-role, activity, and history reads plus health analysis are unchanged. Suggested Salesforce changes are explicitly user-applied. |
| `deal-signals` | Portable output only | Current-user/ObjectInfo grounding and account-owner-scoped open-book sweep are unchanged. Same optional evidence; Markdown signal digest replaces widget-first output. |
| `deal-slip-scenario` | Portable output only | Opportunity grounding, open-quarter pipeline, and closed-won baseline reads are unchanged. The scenario is delivered in Markdown instead of a required widget. |
| `draft-outreach` | Safety clarification | Contact/account/activity Salesforce reads and optional email/docs/Slack evidence are unchanged. The original already said draft, not send; portable adds a specific send-only-mail fallback: return subject/body for copy/paste rather than send. |
| `expansion-whitespace` | Safety clarification | Account/contact grounding and won-opportunity/line-item reads are unchanged. Suggested opportunity shapes are explicitly suggestions for a rep to pursue, not records to create. |
| `find-internal-answer` | **Material** | Adds a concrete, bounded Opportunity lookup by `%TOPIC%`, returning recent matching opportunities, owners, and accounts. It is used only as a pointer to someone who handled a similar deal, never as a policy source. **Why:** gives a Salesforce-only fallback when docs/Slack/email are unavailable and makes the answer actionable without inventing policy. |
| `forecast-narrative` | **Material** | Changes the `OpportunityFieldHistory.CreatedDate` predicate from `%QSTART%` to `%QSTART%T00:00:00Z`. **Why:** `CreatedDate` is a date-time field; the bare date fails Salesforce validation. This restores the history-based movement section. Submission remains manual. |
| `handle-objection` | **Material** | Adds a bounded Opportunity lookup by deal-name fragment, including stage, amount, close date, description, account, owner, and contact roles. **Why:** lets the response cite the customer’s recorded deal context when optional evidence tools are absent. No writes are added. |
| `inbox-sweep` | Safety clarification | Account/open-opportunity context read and inbox classification are unchanged. Adds the same send-only-mail fallback as `draft-outreach`: return copyable reply text rather than send. |
| `lead-triage` | **Material** | Changes Lead `Owner` from a User-only selection to User-or-Group fragments. **Why:** queue-owned Leads otherwise fail the GraphQL owner span; portable output can now identify the queue for routing. Lead/Account reads and triage scoring remain unchanged. |
| `pipeline-review` | Portable output only | Grounding, scoped sample/aggregate, win-rate, missing-next-step, and SOQL fallback queries are unchanged. The same analysis is presented as Markdown. |
| `query-activity-history` | Portable output only | Record resolution and ActivityHistories SOQL query, fields, order, and cap are unchanged. Timeline output is Markdown-first; logging remains a separate workflow. |
| `renewal-radar` | Portable output only | Scope resolution, Opportunity grounding, bounded renewal detail, matching aggregate, and optional evidence reads are unchanged. Portable output preserves the full-book-total versus scored-sample disclosure in Markdown. |
| `rep-context` | Portable output only | Active-user resolution, open-book sample, stage aggregate, activity counts, and won aggregate are unchanged. Slack/calendar evidence stays optional; output is Markdown-first. |
| `research-prospect` | Portable output only | Account grounding, Name-first duplicate check, Website fallback, and web research topics are unchanged. Portable framing makes the duplicate-check/read-only intent explicit. |
| `salesforce-hygiene-check` | Safety clarification | Opportunity grounding and 200-row open-book audit are unchanged. Upstream’s host-specific follow-on updater route is removed; recommendations are explicitly manual rep actions. Audit findings are unchanged. |
| `stakeholder-map` | Safety clarification | Contact grounding, deal resolution, OCR/contact reads, account roster, and optional email/calendar/docs/Slack evidence are unchanged. Portable wording says dark contacts are listed for the rep to add, not created by the skill. |
| `team-pipeline` | Portable output only | User/Opportunity grounding, team resolution, closed-won aggregate, sample/forecast aggregate, hygiene aggregates, and SOQL fallbacks are unchanged. Claude-specific temporary-file/bash recovery text is removed; the Markdown scoreboard is primary. |
| `voice-profile` | Portable output only | No Salesforce reads exist in either version; both analyze sent mail only. The host-specific `/mcp` instruction is removed and replaced with host-email-connector wording. It still neither sends nor writes. |
| `weekly-wrap` | **Material** | Upstream combines six detail roots and six aggregate roots in one GraphQL dispatch. Salesforce limits a request to 10 data fetchers, so the 12-root call fails. Portable keeps every root and filter but splits them into two dispatches: detail and aggregate. **Why:** verified against API v60.0–v68.0 and real Headless 360; the split returns the intended report where upstream fails. Slack remains draft-only. |
| `win-loss-review` | Portable output only | Opportunity grounding, 200-row closed-opportunity read, history child query, scope handling, and optional transcript/email evidence are unchanged. Markdown review replaces widget-first delivery. |

## Material-change detail and evidence

### `daily-briefing`: authoritative totals

- **Upstream:** concrete `first:50` detail reads for closing-soon and past-due opportunities.
- **Portable:** keeps those reads and adds matching aggregate queries for `Id.count` and `Amount.sum`.
- **Impact:** headers and totals cover all matching opportunities; detail rows remain bounded and are labeled as partial when necessary.
- **References:** upstream [`daily-briefing`](../salesforce-for-sales/skills/daily-briefing/SKILL.md#L41); portable [`daily-briefing`](../agent-plugin/skills/daily-briefing/SKILL.md#L28).

### `find-internal-answer`: concrete Salesforce fallback

- **Upstream:** directs a generic Salesforce check for approval/history questions.
- **Portable:** queries recent matching opportunities and surfaces their owners as people to ask.
- **Impact:** a question can return a grounded contact point even without document, Slack, or email connectors; it must not be presented as policy.
- **References:** upstream [`find-internal-answer`](../salesforce-for-sales/skills/find-internal-answer/SKILL.md); portable [`find-internal-answer`](../agent-plugin/skills/find-internal-answer/SKILL.md#L41).

### `forecast-narrative`: date-time repair

- **Upstream:** filters `OpportunityFieldHistory.CreatedDate` with a date literal.
- **Portable:** appends `T00:00:00Z` to produce a valid date-time value.
- **Impact:** restores the history fallback for forecast movement instead of failing its SOQL query.
- **References:** upstream [`forecast-narrative`](../salesforce-for-sales/skills/forecast-narrative/SKILL.md#L74); portable [`forecast-narrative`](../agent-plugin/skills/forecast-narrative/SKILL.md#L74).

### `handle-objection`: grounded deal context

- **Upstream:** says to pull the deal itself but has no explicit Salesforce template.
- **Portable:** adds a bounded deal lookup and safe disambiguation rule.
- **Impact:** objection responses can cite the current deal’s recorded metrics, pain, stakeholders, and next step.
- **References:** upstream [`handle-objection`](../salesforce-for-sales/skills/handle-objection/SKILL.md#L31); portable [`handle-objection`](../agent-plugin/skills/handle-objection/SKILL.md#L33).

### `lead-triage`: queue-owner support

- **Upstream:** selects Lead owner through the User fragment only.
- **Portable:** selects either User or Group.
- **Impact:** queue-owned leads can be read and routed instead of producing an owner-field error.
- **References:** upstream [`lead-triage`](../salesforce-for-sales/skills/lead-triage/SKILL.md#L53); portable [`lead-triage`](../agent-plugin/skills/lead-triage/SKILL.md#L42).

### `weekly-wrap`: valid GraphQL execution

- **Upstream:** sends 12 data-fetcher roots in one request; Salesforce rejects it with `ExecutionAborted` before returning data.
- **Portable:** sends six detail roots and six aggregate roots in separate dispatches, preserving all filters, fields, and aliases.
- **Impact:** weekly-wrap now executes through real Headless 360 and returns details and totals.
- **References:** upstream [`weekly-wrap`](../salesforce-for-sales/skills/weekly-wrap/SKILL.md#L52); portable [`weekly-wrap`](../agent-plugin/skills/weekly-wrap/SKILL.md#L52).

## Conclusion

The portable conversion preserves the upstream sales workflows and optional connector behavior. The primary deliberate changes are:

1. removing Cowork-only widget delivery as a prerequisite;
2. enforcing clearer draft-only and manual-write behavior across hosts; and
3. repairing six concrete execution/data-path gaps: `daily-briefing`, `find-internal-answer`, `forecast-narrative`, `handle-objection`, `lead-triage`, and `weekly-wrap`.

No portable skill newly sends email, posts Slack, or writes Salesforce records.
