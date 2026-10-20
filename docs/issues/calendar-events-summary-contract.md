# calendar-events: Event query cannot support its advertised deal and attendee summary

- **Status:** Submitted upstream as [#20](https://github.com/salesforce/salesforce-skills/issues/20). Reproduced in independent non-production test orgs.
- **Affected skill:** [`salesforce-for-sales/skills/calendar-events/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/calendar-events/SKILL.md)
- **Active mirror status:** Locally diverged in `agent-plugin/skills/calendar-events/SKILL.md` to implement the two corrections in [#20](https://github.com/salesforce/salesforce-skills/issues/20), validated in Quick with synthetic Events; the upstream source remains unchanged.

## Summary

`calendar-events` promises a schedule summary that includes deal-linked counts, deal value and
links, and an external-attendee count. Its documented Event query cannot reliably produce those
outputs:

1. the `What` projection cannot distinguish an Account from an Opportunity or provide the fields
   needed for deal-specific output; and
2. the `Who` projection is not an attendee collection, so it cannot support an external-attendee
   count.

These are separate, reproducible behaviors within the same skill and Event-read/render flow. The
proposed fix is scoped to that skill's query and output contract.

## Shared reproduction conditions

All cases use only synthetic records in a non-production test org and the current user's Events.
The reads use the documented Headless-compatible GraphQL route:

```text
GET /services/data/v66.0/graphql
queryParams.queryInput = {"query":"query { uiapi { query { Event(...) { ... } } } }"}
```

No organization-specific records, users, IDs, or URLs are required to reproduce the results.

## 1. `What` does not support deal grounding

### Minimum setup

1. Create a synthetic Account.
2. Create a synthetic Opportunity under that Account with Amount `70000`, an open stage, and a
   future close date.
3. Create a current-user Event in the query window whose `WhatId` points to that Opportunity.

### Current action

Run the skill's date-filtered `Event(scope: MINE)` query, whose `What` selection is effectively:

```graphql
What {
  ... on Account { Name { value } }
  ... on Opportunity { Name { value } }
}
```

### Observed result

The Event's related record is returned only as:

```json
{"What":{"Name":{"value":"<synthetic opportunity name>"}}}
```

That response has no runtime type, related-record ID, amount, stage, close date, or Account name.
A renderer cannot determine whether the name represents an Account or Opportunity, cannot derive a
deal-linked count, cannot create a related-record link, and cannot populate a currency value.

The following narrow enriched selection succeeds against the same Event:

```graphql
What {
  __typename
  ... on Account {
    Id
    Name { value }
  }
  ... on Opportunity {
    Id
    Name { value }
    Amount { value displayValue }
    StageName { value displayValue }
    CloseDate { value }
    Account { Name { value } }
  }
}
```

It returns runtime type `Opportunity`, the related ID, Amount `70000`, the open stage, the future
close date, and the synthetic Account name.

### Expected result

The skill should query the type and fields required by the output it instructs a host to render.
An Event should be classified as deal-linked only when the returned runtime type is `Opportunity`,
and a value or related-record link should be rendered only from returned Opportunity data.

## 2. `Who` does not support an external-attendee count

### Minimum setup

1. Create a current-user Event with no `WhoId`.
2. Create a synthetic Contact.
3. Add that Contact to the Event as an accepted Event relation.

### Current action

Run the skill's Event query, which reads:

```graphql
Who {
  ... on Contact { Name { value } }
  ... on Lead { Name { value } }
}
```

### Observed result

The Event returns:

```text
Who: null
Attendees: "0"
```

The accepted synthetic Contact attendee exists, but `Who` is null because it is a primary
Contact/Lead relation rather than the attendee collection. The available `Attendees` field also
returns the string `"0"` for this accepted-attendee case. Therefore neither field supports a
complete external-attendee count through the documented query path.

### Expected result

The skill must not label `Who`-based data as an external-attendee count. It should either omit the
metric when no supported participant collection is available, or describe a narrower metric such
as Events with a linked Contact or Lead.

## Narrow proposed upstream fix

In `calendar-events/SKILL.md`:

1. Add `__typename` and `Id` to the `What` fragments; add `Amount`, `StageName`, `CloseDate`, and
   `Account.Name` to the Opportunity fragment.
2. Replace the mandatory external-attendee count with a metric the query can actually support, or
   omit it when no supported attendee source is returned. Do not infer an attendee count from
   `Who` or `Attendees`.
3. Add regression coverage for an Opportunity-linked Event and an Event with an accepted Contact
   attendee but no `WhoId`.
