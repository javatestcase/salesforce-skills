# deal-advance-gap: default target stage relies on a stage order no read returns

- **Upstream issue:** [salesforce/salesforce-skills#24](https://github.com/salesforce/salesforce-skills/issues/24)
- **Status:** Open
- **Affected skill:** [`salesforce-for-sales/skills/deal-advance-gap/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/deal-advance-gap/SKILL.md)
- **Active mirror status:** Applied locally as an approved temporary deviation. The upstream
  source is unchanged.
- **Follow-up comment:** [Posted on #24](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032)
  for the same gap in `deal-review`, whose local copy also carries the fix.

## Summary

Step 2b sets the default target to the deal's next stage ("Target = next stage (default)"), and
step 3 says to infer exit criteria from the org's own data, including the StageName picklist.
No documented read returns the stage order. The step 1 grounding read returns each field's API
name, label, and relationship name, so `StageName` comes back only as its label. The skill also
forbids Salesforce reads beyond its documented ones.

An agent following the skill therefore has to guess the next stage from general sales knowledge,
although stage sequences are configured per org.

## Reproduction — reproduced

### Minimum setup

Any non-production test org with an open Opportunity whose stage is not the last open stage.

### Current grounding read

Run step 1 as written:

```graphql
query {
  uiapi {
    objectInfos(apiNames: ["Opportunity"]) {
      fields { ApiName label relationshipName }
      childRelationships { childObjectApiName relationshipName }
    }
  }
}
```

The `StageName` entry in the response is:

```json
{ "ApiName": "StageName", "label": "Stage", "relationshipName": null }
```

The response contains no stage values or order, and no other documented read returns them.

In two agent runs for the same open deal in the Value Proposition stage, the first named the next
stage "Identify Decision Makers"; the org's label is "Id. Decision Makers". The second named
Proposal/Price Quote, which comes three stages after Value Proposition in that org.

### Same request with the stage order

Add an aliased root to the step 1 request. The grounding selection is unchanged, so this stays
one call:

```graphql
stages: objectInfos(
  objectInfoInputs: [
    { apiName: "Opportunity", recordTypeIDs: ["012000000000000AAA"], fieldNames: ["StageName"] }
  ]
) {
  fields {
    ApiName
    ... on PicklistField {
      picklistValuesByRecordTypeIDs { recordTypeID picklistValues { label value } }
    }
  }
}
```

It returns the Stage values in the org's order, for example:

```text
Prospecting → Qualification → Needs Analysis → Value Proposition → Id. Decision Makers →
Perception Analysis → Proposal/Price Quote → Negotiation/Review → Closed Won → Closed Lost
```

`012000000000000AAA` is the master record type, which lists every active stage. Without
`recordTypeIDs`, the picklist fragment fails with "PicklistField fragment requires a recordTypeId
argument."

This was reproduced in two separate non-production orgs, one Developer Edition and one Enterprise
Edition. All reads used the Salesforce GraphQL API at v65.0, the version the skill uses, both
directly and through the skill's `dispatch_readonly` tool.

## Observed and expected behavior

**Observed:** the default target stage is guessed, and it varied between runs on the same deal,
so the advance plan can aim at the wrong stage.

**Expected:** the default target is the stage that follows the deal's current stage in the org's
own order, taken from a documented read.

## Narrow proposed fix

- Add the aliased `stages` root to the step 1 request. It rides in the same call, so the read
  count does not change.
- Define the default target as the stage that follows the deal's current stage in that list;
  when the next value is Closed Won, the target is to close.
- Orgs with several sales processes can limit a record type to a subset of these stages.
  `recordTypeIDs` also accepts the deal's record type Id for that case, which was not tested.
- Leave the other reads and the widget unchanged.

## Follow-up comment

`deal-review`
([`SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/deal-review/SKILL.md))
has the same gap. Its widget's stage tile asks for the deal's stage position (`kpiStageNum`, for
example `06`) and the stages left to close (`kpiStageSub`, for example "1 stage to close"). Its
step 1 grounding read also returns `StageName` only as a label, and no other read returns the stage
order. In an agent run on a Value Proposition deal, the tile showed the correct position only
because the test org uses the default stages, and the sublabel read "mid-funnel" instead of the
stages remaining. Adding the same aliased `stages` root to its step 1 request, and taking both
values from it, fixes it there: it returned the org's ten stages in order, giving position 04 and
five stages to close.
