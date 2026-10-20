# handle-objection: resolve the supplied deal before grounding a response

- **Upstream issue:** [salesforce/salesforce-skills#19](https://github.com/salesforce/salesforce-skills/issues/19)
- **Status:** Open
- **Evidence status:** Suspected source-contract gap from static inspection; not a live-org reproduction.
- **Affected skill:** [`salesforce-for-sales/skills/handle-objection/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/handle-objection/SKILL.md)
- **Active mirror status:** Not applied locally. This report does not change the active mirror.

## Summary

`handle-objection` promises a response grounded in “the deal itself,” but it currently provides no
Opportunity lookup or exact-Id detail request. Its evidence section names the deal as an evidence
source without documenting how to resolve a supplied deal or retrieve the customer's stated goals
and contacts.

## Safe scenario demonstrating the missing contract

In a non-production test org, create two open Opportunities whose names share a phrase but whose
accounts, stages, amounts, and close dates differ. Ask for help responding to an objection about
that shared phrase.

The skill has no documented action shape for:

- listing a bounded set of matching candidates;
- detecting multiple candidates and asking the user to choose; or
- reading the selected Opportunity by its exact Id for the description, account, and contact roles
  needed to ground the response.

Because the skill prohibits undocumented API calls, an agent cannot supply those CRM facts without
guessing an unsupported lookup.

## Expected behavior

1. If the user supplies an Opportunity Id, read that exact record.
2. Otherwise, use a bounded candidate lookup (for example, at most 10 rows) that returns only
   enough context to identify a deal: account, name, stage, amount, and close date.
3. Continue automatically only when exactly one candidate matches. For several candidates,
   present the candidates and ask the user which deal they mean.
4. After selection, read the Opportunity by exact Id, including the stated goals/description and
   contact roles, before using it as objection evidence.

## Narrow proposed upstream fix

Add a two-stage read-only deal-resolution flow to
`salesforce-for-sales/skills/handle-objection/SKILL.md`:

- resolve an Id directly or through a bounded candidate query;
- require explicit disambiguation for multiple matches;
- fetch the richer deal context only by the selected exact Id; and
- add evaluation coverage for zero, one, and multiple candidate outcomes.

This keeps the skill read-only and prevents a response from claiming deal grounding when the
intended Opportunity was never resolved.
