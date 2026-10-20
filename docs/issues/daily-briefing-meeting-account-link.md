# daily-briefing: Opportunity-linked meetings cannot be matched to their account

- **Upstream issue:** [salesforce/salesforce-skills#22](https://github.com/salesforce/salesforce-skills/issues/22)
- **Status:** Open
- **Affected skill:** [`salesforce-for-sales/skills/daily-briefing/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/daily-briefing/SKILL.md)
- **Active mirror status:** Applied locally as an approved temporary deviation. The upstream
  source is unchanged.

## Summary

Step 3 resolves each meeting's account. For a meeting whose `WhatId` is an Opportunity (`006…`),
it says to use "its `AccountId`", but no documented read returns that value. Step 2a selects only
`WhatId` and `WhoId`, and the step 3 Account read matches either an Account Id or an attendee
domain. The skill's global rules also forbid calling any query not written in the skill.

A meeting linked to an Opportunity, with no attendee domain in `Location` or `Description`,
therefore matches no account. The skill then renders it as
`(no CRM match — net new or personal)`, even though Salesforce already links the meeting to an
account.

## Reproduction — reproduced

### Minimum setup

In a non-production test org, acting as the current user:

1. Create an Account with two open Opportunities.
2. Create an Event for today, owned by the current user. Set `WhatId` to one of those
   Opportunities, leave `WhoId` and `Location` blank, and use a `Description` without an email
   address.

### Documented reads

Run the step 2a Event read as written. The selection below is reduced to the relevant fields;
the scope, filter, cap, and ordering match the skill.

```graphql
query {
  uiapi {
    query {
      Event(
        scope: MINE
        where: { ActivityDate: { eq: { literal: TODAY } } }
        first: 50
        orderBy: { StartDateTime: { order: ASC } }
      ) {
        edges {
          node {
            Id
            WhatId { value }
            WhoId { value }
            Location { value }
            Description { value }
          }
        }
      }
    }
  }
}
```

It returns:

```text
WhatId: 006… (the Opportunity)
WhoId: null
Location: null
Description: no email address
```

Step 3 needs an Account Id for `Id: { in: [...] }` or an attendee domain for
`Website: { like: ... }`. Neither is available, and the skill documents no read that maps the
Opportunity to its account. Followed as written, the skill reports this meeting as
`(no CRM match — net new or personal)`.

### Same read with Event `AccountId`

Add the standard `AccountId` field to the same selection:

```graphql
node {
  Id
  WhatId { value }
  WhoId { value }
  AccountId { value }
  Location { value }
  Description { value }
}
```

It returns:

```text
AccountId: 001… (the Opportunity's Account)
```

Passing that Id to the unchanged step 3 Account read returns the Account and both open
Opportunities. Passing the Event's `WhatId` to the same read instead returns no Account, so the
existing `Id` predicate cannot use the Opportunity link directly.

This was reproduced in two separate non-production orgs, one Developer Edition and one Enterprise
Edition. All reads used the Salesforce GraphQL API at v65.0, the version the skill uses, both
directly and through the skill's `dispatch_readonly` tool.

## Observed and expected behavior

**Observed:** the documented reads cannot connect an Opportunity-linked meeting to its account.
The briefing labels the meeting as having no CRM match unless the agent breaks the skill's rule
against undocumented queries. In an agent run on the same kind of data, the meeting card showed an
Opportunity field that no documented read selects, so the agent had gone outside the skill's
reads. The card still omitted the account's other open Opportunity.

**Expected:** the meeting resolves to its Opportunity's Account, and the meeting context lists
that Account's open Opportunities, using only documented reads.

## Narrow proposed fix

- In step 2a, add `AccountId { value }` to the Event selection. Salesforce populates this
  standard, read-only field from the record the Event is related to.
- In step 3, put each non-null Event `AccountId` in the Account read's `Id: { in: [...] }`
  predicate. Keep the `Website` domain match as the fallback for meetings without one.
- Keep `WhatId` to identify the specific linked record.
- Leave the widget, renderer JSON, and other reads unchanged.

Reference: the `AccountId` field in the
[Event object reference](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_event.htm).
