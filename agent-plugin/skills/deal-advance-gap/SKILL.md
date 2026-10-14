---
name: deal-advance-gap
description: "Map an opportunity's path to advance or close from Salesforce stage, stakeholder, activity, qualification, and risk data plus email, documents, and Slack. Use to diagnose a stuck deal, identify blockers and owners, or test whether its close date is credible."
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

# Rules

- Apply the human-label rule to Opportunity child records too. State a risk as "Blocking: yes · Severity: High · Status: Mitigating", never `Is_Blocking__c = true`.

# Deal Advance Gap

Forward-looking: against the org's stage exit criteria, what has to happen for this deal to advance — and the shortest path to it. Ground → resolve to one Id (+ evidence, ONE turn) → detail read → map gaps → sequence → output. **Read-only:** this skill never writes to Salesforce; it only reads and reports the path.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields + childRelationships reveal this org's stage/qualification/next-step schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label relationshipName } childRelationships { childObjectApiName relationshipName } } } }\"}" })
```

Step 1 is the authority on names. Note: (a) scalar `__c` fields carrying stage-exit / next-step / blocker / qualification signal — take `{ value }` **and keep each field's `label`**; (b) each lookup's exact `relationshipName` for spanning a related name; (c) each child `relationshipName`. **Build an ApiName→label map now and use the `label` in ALL output** (e.g. "Executive Sponsor", not `Executive_Sponsor__c`; "Target Resolution Date", not `Target_Resolution_Date__c`) — never print a `__c` API name to the user.

## 2a. Resolve to ONE opportunity Id (before the detail read)

Given an SFDC **Id** already → skip to 2b with `Id: { eq: "<Id>" }`. Given a **name**, resolve it first — `first: 1` on a `Name like` only caps the response; it does **not** pick the right deal, so on a multi-match it returns an arbitrary one. Run a bounded, ordered candidate query (`%DEALNAME%` = 1–2 distinctive words):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Name { value } } } } } } } }\"}" })
```

- **Exactly one** candidate → take its `Id`, go to 2b.
- **Several** → list them (Account · Name · Stage · $ · close) and **ask which**; don't guess.
- **None** → broaden `%…%` and retry once.

## 2b. Read the resolved opp by Id (fill from step 1)

Filter by the **exact Id** from 2a (`first: 1` is correct here — the filter is a unique record Id). **Reference-field rules (avoids the retry loop):**
- Scalar/`__c` → `Field__c { value }`. `displayValue` is null for Id fields — don't rely on it.
- Related record's name → span the exact `relationshipName` from Step 1: `<relationshipName> { Name { value } }`. Do NOT append `{ … }` to a raw `Id`/`__c` field.
- No usable relationshipName → take the `__c { value }` (Id) and move on — **do not retry**.

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed relationship (`<relationshipName> { Name { value } … }` for a lookup; `<childRelationshipName> { edges { node { … } } }` for a child). Standard fields + `OpportunityContactRoles` always work.

**Before dispatching, double-check the query's braces balance** (count `{` vs `}` — they must be equal). Splicing `<OPP_CUSTOM>`/`<REL_BLOCKS>` is where a `}` gets dropped; keep the read flat (no unnecessary nesting).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } ForecastCategory { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } Tasks(first: 15, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Status { value } Description { value } TaskSubtype { value } } } } Events(first: 10, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } } } }\"}" })
```

Target = next stage (default) or "to close" if asked.

**Retry contract on `InvalidSyntax` / "offending token `<EOF>`" (the dynamic splice dropped a brace):** construct **one** corrected query and issue it **only if its text differs** from the failed one (add the missing `}` — never re-send byte-identical text; an identical retry just burns a round-trip for the same error). If that corrected retry still fails, **stop retrying the spliced shape** — fall back to the fixed, guaranteed-field query below (standard fields + contact roles only, no `<OPP_CUSTOM>`/`<REL_BLOCKS>`), then continue the analysis and note that optional custom risk signals were unavailable:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } ForecastCategory { value } LastActivityDate { value } Account { Name { value } } Owner { Name { value } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } } } } } } }\"}" })
```

## 2c. Evidence (run IN PARALLEL with 2a — same turn, issue all at once)

**Issue 2a and all of 2c in a single turn** — these searches key on the deal/account name from the *request* (not the SF read), so batch them with candidate resolution; only 2b's detail read waits on the resolved Id. Keyed on the deal/account:
- **email**: last exchange per contact, open commitments in both directions, silence/OOO/departure
- **docs**: latest transcript/notes → decisions, objections, open commitments, competitor mentions
- **slack**: internal blockers — deal desk, legal, security review, pricing approval

Use whatever email/doc/Slack tools are present; if none, skip silently (SF-only is fine). Cite source + date for anything used.

**No extra Salesforce reads.** 2b already returned the CRM state (stage, close, next step, probability, forecast, last-activity, contact roles, recent Tasks/Events, `__c` signals). Do NOT issue a **separate** per-opp SF follow-up (a standalone `ActivityHistory` / `OpportunityFieldHistory` / Task query) — recent activity already rides along as the `Tasks`/`Events` child edges in the 2b query (same round-trip, no extra call). Read those children as distinct states: a completed Task (Status Completed / past-dated Event) is a done touch; an open Task or a future-dated Task/Event is **🔶 In motion / scheduled**, not done — that's the signal behind "Already in motion". Deeper detail comes from the external evidence above.

## 3. Map gaps against exit criteria (cite every claim; invent nothing)

Exit criteria, qualification framework, and required-stakeholders-for-close are **external knowledge** — infer from the org's own data (StageName picklist, closed-won patterns) or ask the user once. Never invent. For the current stage's exit criteria (and every later stage if target is "to close"), mark each: **✅ Done / 🔶 In motion / ❌ Not started**, with the source and the specific gap. Then check the qualification framework the same way — flag only elements that **block advancement**, not every unknown.

## 4. Sequence the path

Order gaps into the shortest credible path: whose gap (Us / Customer / internal team), parallel vs. strictly sequential, and the single next action that unblocks the most downstream items. Critical-path length → earliest credible close; flag if that lands after the current CloseDate.

## 5. Output — advance-gap plan (primary, portable)

Assemble the plan as Markdown. This is the deliverable in any host. Cite the source + date behind every gap and status; keep the three activity states (✅ Done / 🔶 In motion / ❌ Not started) distinct.

```
# Advance Gap: <Name> — <current stage> → <target>
**Short answer:** <1–2 lines: advances when X and Y; critical path runs through Z>

## Readiness
- <M> of <N> exit criteria complete · <count> open · <count> blocking

## Gaps blocking advancement
| # | Gap | Owner (Us/Customer/team) | State (Done/In motion/Not started) | Blocking (gate/close req) | Evidence (source+date) |

## Already in motion
- <underway items + expected landing — don't re-ask>

## The path
1. <action — who — by when> (unblocks #n)
   Critical path ~<N> weeks → earliest credible close <date> (flag if after CloseDate)

## Suggested SFDC updates (for the rep to apply)
- NextStep → "<the #1 action>" · CloseDate → <if path math says current date isn't credible>
```

Link the opportunity inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`).

## 6. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a readiness-meter/gap-checklist visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 5 is the whole deliverable.
