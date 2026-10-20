# Questions for the Amazon Quick team

## Context

We're adapting the 31 Salesforce sales skills in
[salesforce/salesforce-skills](https://github.com/salesforce/salesforce-skills), plus their 3
helper skills (`configure`, `update`, and `using-display-widget`), to run in Amazon Quick. We ran
them in Quick against synthetic Salesforce data, with Salesforce's Headless 360 MCP server as the
connector. Quick ran the skills' Salesforce reads and rendered Salesforce widgets for the ones that
use them.

Some of Quick's behavior took extra work. Seven skills now carry Quick-specific rules in our local
copy, and we reported the bugs that affect any host upstream as GitHub issues. The questions below
are the ones we couldn't answer from our side. Each notes what we saw.

## Questions

The questions are ordered by importance. The first three bear on most of the local rules we added
and on how we check runs.

1. **Run traces: Can we export a run's full trace, with every tool call's arguments and result?**
   The step list hid details we needed to verify, such as the search phrase deal-review used and
   whether the email searches ran.
2. **Instruction priority: How do skill instructions rank against Quick's own system prompt?** Quick
   narrated between tool calls although the skills say not to. It ran a Salesforce search that
   customer-voice doesn't include, and it dropped 3 of 21 flagged deals to shorten a deal-signals
   digest.
3. **Exact templates: Can a skill ship a script or template file that Quick reads or runs exactly
   as written?** Quick rewrote long GraphQL queries and broke their braces in account-context and
   customer-health. It also edited widget JSON it was told only to fill in, relabeling
   deal-review's buttons.
4. **Tool availability: What decides which tools a run gets?** Some runs used the email tool, while
   others in the same setup made no email call. `display_widget` didn't appear until the connector
   configuration changed.
5. **Write and send approval: How does Quick confirm MCP writes and email sends?** Three skills
   (draft-outreach, call-follow-up, and inbox-sweep) must only create drafts. We've seen two of
   them handle a missing email connector correctly, but we haven't seen one create a draft.
6. **Skill loading: Does Quick load a whole `SKILL.md` into context, or only parts of it?** Ours
   run up to about 950 lines, with large embedded JSON. Some runs skipped steps the skill spells
   out, and we'd like to rule out truncation.
7. **Batch evaluation: Can we batch-run a fixed set of prompts against a pinned model?** Several
   failures were intermittent, and we've been running prompts by hand and copying the results.
8. **Installation and routing: What's the supported way to install a package of many skills?** Ours
   uses the Agent Plugins layout (`plugin.json`, `mcp.json`, and 31 skills plus 3 helpers). How
   does Quick choose among installed skills, and is there a limit on how many it can choose from?
9. **Run summary: What do "Read 1 file," "used knowledge graph," and "loaded 2 skills" mean?** One
   deal-review run showed all three. Which file and skills were they, and what does the knowledge
   graph add? One daily-briefing run showed a Salesforce field that none of the skill's queries
   select.
10. **Calculations: Is there a calculation or code tool skills can rely on?** Totals and rankings
    were wrong in three runs across two skills. For example, one digest gave an overdue total of
    $2.1M when the deals it listed summed to $2,364,000.
11. **Widget sandbox: What sandbox does Quick run MCP App widgets in, and is that support stable?**
    The Salesforce renderer hangs in opaque-origin sandboxes, such as the MCP Apps basic host and
    MCP Inspector, but it rendered in Quick.
12. **Widget buttons: Do `sendMessage` and `openLink` actions work?** The Salesforce widgets use
    both, and we haven't tried either in Quick.
13. **Tool arguments: How does Quick pass object-type arguments to MCP tools?** In one of three
    customer-health runs, `widgetDefinition` was sent as a JSON string instead of an object. The
    tool rejected it, and the retry worked.
14. **Final output: Can a skill make a tool call its final output?** Every widget skill says the
    widget is the last thing shown, and Quick still adds a recap sentence after it.
