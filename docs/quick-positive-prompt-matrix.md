# Proposed Quick workflow prompt matrix

This matrix covers the 31 end-user workflow skills. It intentionally excludes the three utility
skills: `configure`, `update`, and `using-display-widget`. Expected results are proposed host-run
contracts, not evidence that Quick has installed, routed, or rendered the plugin.

| Skill | Prompt | Expected Result |
|---|---|---|
| `account-context` | `Tell me about the Ravelin Rail Logistics account.` | A Salesforce account brief with Ravelin’s open and closed opportunities. |
| `account-tiering` | `Rank my accounts into action tiers.` | Bill Tarr’s accounts ranked from Salesforce fit, activity, contacts, and opportunity data. |
| `calendar-events` | `Show my Salesforce Event schedule for October 19, 2026, including any linked accounts or opportunities.` | Two October 19 `Exec briefing` Salesforce Event records related to Orrin Petroleum Group, rendered in the Salesforce current user’s timezone; no Google/Outlook calendar reads or calendar writes. |
| `call-follow-up` | `Create a follow-up for my call with Avery Ravelin at Ravelin Rail Logistics. Transcript: “We agreed to schedule a technical deep dive next week. Avery will send the current site requirements on Friday. We will send the revised proposal and implementation outline. Avery asked for clarity on the renewal timeline.”` | A Salesforce-grounded customer email and internal Slack summary as drafts, or copyable draft text if no draft-capable connector is available. |
| `call-prep` | `Prep me for my October 19, 2026 exec briefing with Orrin Petroleum Group.` | A meeting brief using the Orrin event, opportunity, account, and activity context. |
| `close-plan` | `Build a close plan for Corvane Micro Devices — New Business Plant Upgrade.` | A close plan for the open $1.296M Value Proposition opportunity. |
| `customer-health` | `Assess the health of Halcrest Municipal Utilities.` | A health assessment using the account’s high-priority generator-alert cases and open opportunities. |
| `customer-voice` | `What are customers saying about generator reliability across our accounts?` | Attributable customer themes and quotes if Quick has call-transcript, email, or document sources; otherwise a clear source-availability limitation. |
| `daily-briefing` | `Give me my sales briefing for October 19, 2026.` | A daily Salesforce briefing using Bill’s pipeline, Orrin tasks, and events. |
| `deal-advance-gap` | `What has to happen to advance Corvane Micro Devices — New Business Plant Upgrade?` | Evidence-backed stage-exit gaps and next actions for the $1.296M opportunity. |
| `deal-review` | `Review the health of Corvane Micro Devices — New Business Plant Upgrade.` | A scored deal-health assessment using current fields, activities, contacts, and account history. |
| `deal-signals` | `Which of my deals need attention right now?` | A prioritized list of Bill’s stale, incomplete, or risky deals. |
| `deal-slip-scenario` | `Model the impact if Corvane Micro Devices — New Business Plant Upgrade slips out of this quarter.` | The forecast/pipeline impact of the $1.296M opportunity slipping, plus backfill options. |
| `draft-outreach` | `Draft outreach to Avery Ravelin at Ravelin Rail Logistics about the Renewal Backup Power opportunity.` | A personalized email draft using Avery’s Salesforce contact, account, and opportunity context; never sent. |
| `expansion-whitespace` | `Where is the expansion whitespace at Corvane Micro Devices?` | Expansion opportunities based on Corvane’s open opportunities and historical wins/losses. |
| `find-internal-answer` | `Who owns the Ravelin Rail Logistics account in Salesforce?` | The Salesforce account owner, Bill Tarr; Quick may add internal-document, Slack, or email evidence if configured. |
| `forecast-narrative` | `Walk me through my forecast for this quarter.` | A narrative of Bill’s forecast, key deals, movement, risks, and asks. |
| `handle-objection` | `Corvane Micro Devices says the $1.296M Plant Upgrade is too expensive. Help me respond.` | A grounded price-objection response using the current deal and win/loss history. |
| `inbox-sweep` | `Sweep my inbox and draft up to five replies.` | Classified email items and up to five drafts if Quick has inbox access; no messages sent. |
| `lead-triage` | `Triage the existing lead Bertha Boxer at Farmers Coop. of Florida.` | A priority/routing assessment for the existing `Working - Contacted` lead. |
| `pipeline-review` | `Review my pipeline health.` | Bill Tarr’s pipeline health, risks, coverage, and prioritized actions. |
| `query-activity-history` | `Show the activity history for the Orrin Petroleum Group — Expansion Plant Upgrade opportunity.` | A dated timeline of the opportunity’s Salesforce tasks and events. |
| `renewal-radar` | `Scan my upcoming renewals.` | Renewal risks and next moves across Bill’s Ravelin, Brightfell, Kestrel, and other renewal opportunities. |
| `rep-context` | `Prep me for a 1:1 with Ramon Diez.` | Ramon Diez’s open book, recent activity, coaching opportunities, and suggested 1:1 questions. |
| `research-prospect` | `Research Snowflake before I reach out.` | A net-new prospect brief using web research; requires Quick web-research access. |
| `salesforce-hygiene-check` | `Check my pipeline data quality.` | Prioritized data-quality fixes for Bill’s incomplete, stale, or inconsistent open opportunities. |
| `stakeholder-map` | `Map the stakeholders on Corvane Micro Devices — New Business Plant Upgrade.` | A stakeholder map from Corvane contacts, opportunity context, and available engagement evidence. |
| `team-pipeline` | `Review my team’s pipeline before the forecast call.` | A team pipeline brief if Quick can resolve a team roster; the current Salesforce fixture has no `ManagerId` relationships. |
| `voice-profile` | `Build my voice profile from my sent email.` | A reusable writing-style profile if Quick has sent-email access; no email is sent. |
| `weekly-wrap` | `Give me my weekly wrap.` | A recap of Bill’s pipeline movement, meetings, and priorities; email/docs/Slack enrichment is optional. |
| `win-loss-review` | `Run a win-loss review for Q2 2026.` | A Q2 win/loss analysis using Bill’s closed opportunities across Coralinde, Corvane, Kestrel, and Ostvold. |
