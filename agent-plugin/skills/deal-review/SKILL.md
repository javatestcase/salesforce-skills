---
name: deal-review
description: "Build a scored deal-health assessment from Salesforce fields, contacts and activity plus email, documents and Slack, with evidence-backed risks. Use to judge whether one deal will close; for stage-exit gaps and a sequenced path, use deal-advance-gap."
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

# Deal Review

Ground → (read + evidence searches, all in ONE turn) → analyze. **Read-only:** this skill never writes to Salesforce; it produces a health read and suggested changes for the rep to apply themselves.

## 1. Ground (hardcoded — Opportunity only)

Ground `Opportunity`. Its fields reveal this org's custom deal signals; the fixed standard history query below needs no metadata.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings from it, never guess. Select relevant `__c` fields (health, next-step, exec-sponsor, forecast, risk signals, etc.) as `{ value }` and keep each field's `label`. **Build an ApiName→label map now and use the `label` in ALL output** (e.g. render `Executive_Sponsor__c` as "Executive Sponsor", `Health_Score__c` as "Health Score") — never print a `__c` API name to the user.

## 2. Read (fill from step 1)

`%DEALNAME%` = 1–2 words. A confirmed `__c` field → `Field__c { value }`; do not invent or span custom relationships.

Insert `<OPP_CUSTOM>` = relevant confirmed `__c { value }` fields. Standard fields and `OpportunityContactRoles` always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } Type { value displayValue } Probability { value } ForecastCategory { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } Tasks(first: 15, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Status { value } Description { value } TaskSubtype { value } } } } Events(first: 10, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } OpportunityHistories(first: 200, orderBy: { CreatedDate: { order: DESC } }) { edges { node { CreatedDate { value } StageName { value } Amount { value displayValue } PrevAmount { value displayValue } CloseDate { value } PrevCloseDate { value } } } } } } } } } }\"}" })
```

Empty `edges` → use a broad resolver selecting only `Id Name { value }`, choose the target, then rerun the full template with `where: { Id: { eq: "<ID>" } }`; never run the rich template across multiple matches. The `orderBy: { CloseDate: { order: DESC } }` makes `first: 1` favor the active/current deal on a multi-match name (not an arbitrary stale closed-won). `Task.Description`/`TaskSubtype` carry the "what happened" detail behind each timeline row. The `Tasks`/`Events` children carry the activity timeline — read them as **three separate states** (see next paragraph); a scalar `LastActivityDate` alone can't distinguish an open task or a future meeting from a completed touch.

**Deal history (included in the read above).** The nested `OpportunityHistories` snapshots are already scoped to the selected Opportunity, so they ground whether the CloseDate moved and detect same-day stage jumps without an ID-dependent second read.
A snapshot dated *this* cycle with `CloseDate` different from `PrevCloseDate` = real slippage (penalize); no recent CloseDate change with the current date holding = inherited history, not a current slip (context only). Same-day StageName jumps = signals to surface. Empty/unavailable → don't infer a slip.

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b as tool calls in a single turn — do not wait for the SF read to return before firing the searches.** They're independent (searches key on the deal/account name, not the SF result), so batch them together. Keyed on the deal/account name:
- **email**: threads with the account/contacts, last ~60d → last exchange date + topic, objections, commitments
- **docs**: recent transcripts/notes on the account → decisions, objections, competitor mentions
- **slack**: internal mentions → deal-desk/exec/concerns

Use whatever email/doc/Slack search tools are available. If none are present, skip silently (SF-only is fine). Never block on these; cite source + date for anything you use.

## 3. Analyze (cite every value/source; invent nothing)

Signal-adjust from SFDC `Probability`, only on a shown trigger:
`+5` ≥3 contact roles · `+10` economic buyer role · `+10` champion engaged (multiple completed touches, email/Task) · `+10` mutual close plan / exec engaged (email/doc) · `−10` >14d since last **completed** touch · `−15` CloseDate past · `−15` open blocking risk · `−10` open High-sev risk · `−10` single-threaded · `−10` champion quiet 14d+ (email) · `−10` competitor named (doc/email) · `−10` current-cycle CloseDate slip (see guardrail). Floor 5, ceil 95. Show the math.

**Activity — three states, never conflated** (read from the Tasks/Events children, not `LastActivityDate` alone): *completed* = Task `Status` Completed or past-dated Event; *open* = Task not yet Completed; *scheduled* = any Task/Event dated after today. "Days dark", the `−10 >14d`, and `−10 champion quiet` triggers key on the last **completed** touch only — a future QBR or an open task is momentum, not a completed touch, and never resets the clock or counts as one. Surface open tasks and scheduled meetings as positive momentum, not silence.

**Match every adjustment to shown state; current-cycle only.** Apply a trigger only if the data you pulled shows it. Apply the slip penalty only when the deal-history query above shows the *current* CloseDate moved this cycle — a PushCount / stage-cycling count inherited from earlier cycles, with the current date holding, is **not** current slippage; don't penalize it (note it as historical context instead). Distinguish a confirmed blocking risk from one that's merely stale or unknown — don't score both as equally blocking.

Report any grounded `Executive Sponsor` by name.

## 4. Output — deal review (primary, portable)

Assemble the review as Markdown. This is the deliverable in any host. Cite the source per row; quote blank fields as blank rather than inventing.

```
# Deal Review: <Name> — <Account>
## Health: 🟢/🟡/🔴 <X>/10 — <one-sentence verdict>
<Stage displayValue> · <Amount displayValue> · <Type> · close <CloseDate> · age <days since CreatedDate>d
Prob: SFDC <P>% → adjusted <Y>% (<±adj: evidence>…). If evidence is genuinely two-sided, say so rather than forcing a single precise number.

## Qualification (BANT/MEDDIC)
| Element | Status | Evidence |
|---|---|---|
| Budget | ✅/⚠️/❌ | <$X confirmed <date>, source / gap> |
| Authority | ✅/⚠️/❌ | <EB name, role, source / gap> |
| Need | ✅/⚠️/❌ | <driver, source / gap> |
| Timeline | ✅/⚠️/❌ | <customer close driver, source / gap> |
Cite the source per row; ❌ only when truly not pulled.

## Strengths
- 1–3 evidenced positives (confirmed BANT, prior wins, engaged champion, momentum) — always populate when present; don't drop positives while keeping risks.

## Activity Timeline
- <date> · <source> · <subject / what happened>  (newest first, from the Tasks/Events children)
- Last **completed** touch: <N>d ago · open tasks: <subject, due> · scheduled: <meeting, date>
Keep the three states separate; a scheduled/open item is not a completed touch.

## Risks
- <Primary confirmed gate (Sev, Status, owner)>; then each open risk <Name (Sev, Status, blocking?)>. Mark confirmed-blocking vs stale/unknown distinctly.

## Missing
- Qualification gaps, single-threading, no MAP, unnamed competitor, missing exec sponsor, procurement owner — whatever affects closure.

## Stakeholders
- <Name (Title, Role)>…

## Stage check
- <matches / ahead of evidence — why>

## Evidence
- <key email/doc/Slack signals w/ date+source, or "CRM only — email/docs/Slack not connected">

## Recommended Next Actions
1. 2–4 actions, each tied to a named gap/risk above with an owner or date

## Suggested SFDC changes (for the rep to apply)
- StageName/NextStep/CloseDate where evidence differs from the record — presented as suggestions only; this skill does not modify Salesforce.
```

Link the opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

## 5. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a health-score/MEDDIC visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 4 is the whole deliverable.
