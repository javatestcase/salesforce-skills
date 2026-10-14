---
name: deal-signals
description: "Build a deal-risk digest from Salesforce close dates, activity, next steps and forecast fields plus email, documents and Slack. Use to find quiet or overdue deals, close-date danger, renewal windows, competitor mentions or other risks needing attention."
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

# Deal Signals

Ground → (read + evidence, one turn) → check thresholds → digest. Scope: my book (default), or a tier/team if asked. Since: last run, else 7 days. **Read-only:** this skill never writes to Salesforce; it surfaces risks and hands any follow-up to the rep.

## 1. Ground (hardcoded — Opportunity only) + running user's Id

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's custom signal fields — don't assume names. Fetch `currentUser.Id` in the SAME call (used to account-scope the book in step 2), so this stays one round-trip:

```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Record `currentUser.Id` as `<UID>`. Note scalar `__c` fields relevant to signals (renewal date, competitor, champion, deal-desk/legal-hold). **Resolve the next-step field `<NEXTSTEP>` — prefer a custom field over standard `NextStep`:** first a `__c` field whose `label` or ApiName reads like a next step (e.g. `Next_Step__c` labeled "Next Step"); else the standard `NextStep`. A custom next-step field implies the org built its own next-step logic and reps actually fill it in, whereas the standard `NextStep` is frequently left empty — preferring the custom one is why the "stale commitment" signal fires on the field reps actually use, not a permanently-blank standard one. Use exact names from this result.

## 2. Read the open book (one call, scope: MINE)

`scope: MINE` = the running user's book (no user lookup needed). Add confirmed `__c { value }` fields into `<OPP_CUSTOM>`, and select the resolved next-step field as `<NEXTSTEP> { value }` (default `NextStep { value }`). **Also account-scope the book:** add `Account: { OwnerId: { eq: \"<UID>\" } }` to the `where` so the sweep only covers opps on accounts the rep currently owns. When an account is reassigned, Salesforce moves `Account.OwnerId` but not the open opps' `OwnerId`, so `scope: MINE` alone keeps surfacing stale "zombie" deals on accounts the rep no longer manages. For a tier/team scope (asked for explicitly), drop `scope: MINE` AND this account-owner clause and filter on the requested owner/team instead — a manager reviewing a team wants every deal regardless of account owner.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, Account: { OwnerId: { eq: \\\"<UID>\\\" } } }, first: 100) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } <NEXTSTEP> { value } LastActivityDate { value } LastModifiedDate { value } ForecastCategory { value } <OPP_CUSTOM> Account { Name { value } } } } } } } }\"}" })
```

## 2b. Evidence (same turn, only for CRM-flagged accounts — keeps the sweep fast)

After threshold checks flag accounts, in ONE turn fire (parallel, if tools present): **email** (last reply from us / **inbound from them with no reply from us in 3+ business days** / bounce / OOO / departure), **docs/transcripts** (competitor mention), **slack** (deal-desk/exec concerns). Keyed on the flagged account names. No tools present → skip silently.

**No extra Salesforce reads.** Step 2 already returned every CRM field the thresholds need (LastActivityDate, CloseDate, LastModifiedDate, NextStep, ForecastCategory, `__c` signals). Do NOT issue per-opp SF follow-ups (EmailMessage / Task / OpportunityFieldHistory / activity queries) — each is a serial round-trip. Evidence here is ONLY the external email/doc/slack connectors above; if those aren't present, skip.

## 3. Check thresholds (compute explicit dates from today — never quarter-relative)

Per open opp, fire a signal only when the record shows the trigger:
- **Gone quiet** — LastActivityDate >14d ago (or null) AND CloseDate within 90d
- **Inbound waiting** — customer emailed us and we haven't replied in 3+ business days (email evidence; the ball is on our side)
- **Danger zone** — CloseDate ≤21d out and stage still early
- **Overdue** — CloseDate < today
- **Slipped** — CloseDate moved out / recent LastModifiedDate date change
- **Stale commitment** — NextStep unchanged 21d+
- **Champion risk** — primary contact left/quiet (email/OOO evidence)
- **Renewal opening** — renewal entering lead-time window
- **Competitor mention** — named in recent email/transcript

## 4. Output — deal-signals digest (primary, portable)

Assemble the digest as Markdown. This is the deliverable in any host. Per fired signal, surface the trigger value **plus one or two supporting facts** from the Step 2 record (all already fetched — no new read), separated by ` • ` so the evidence is scannable, not a single condensed fact. Blank line between the 🔴 and 🟡 groups.

```
# Deal Signals — <today> — <scope>

🔴 Act today
- **<Account / Opp>** — <signal> — <StageName label> • $<Amount> • close <CloseDate> • last activity <LastActivityDate> • next step <NextStep> → <action>

🟡 This week
- **<Account / Opp>** — <signal> — <trigger value> • <supporting fact> • <supporting fact> → <action>

✅ Nothing else crossed a threshold (<N> opps swept)
```

Link each record inline (`https://[instanceUrl]/lightning/r/Opportunity/[Id]/view`). Hand any follow-up off: a CRM fix is a suggestion for the rep; a touch is handed to `draft-outreach`/`schedule-meeting`. Scheduled run: lead with the count of new items since last run; a quiet digest is success.

## 5. Rich visualization (host-specific — optional)

If the host provides a rich rendering surface (e.g. Amazon Quick dashboards or Apps in Quick), a signal-score/trend visual may be rendered **in addition to** the Markdown above. That layout is not part of the portable skill — see the plugin's host-extension directory (`com.salesforce.quick/ui`). When no rich surface is available, the Markdown in Step 4 is the whole deliverable.
