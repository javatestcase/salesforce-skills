# daily-briefing: capped detail rows can misstate count and dollar totals

- **Upstream issue:** [salesforce/salesforce-skills#18](https://github.com/salesforce/salesforce-skills/issues/18)
- **Status:** Open
- **Affected skill:** [`salesforce-for-sales/skills/daily-briefing/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/daily-briefing/SKILL.md)
- **Active mirror status:** Not applied locally. This report does not change the active mirror.

## Summary

`daily-briefing` reads closing-soon and past-due Opportunities with `first: 50`, but its
widget labels and text fallback call for unqualified count-and-dollar output. The skill does not
request a population aggregate or pagination metadata, so a 50-row result cannot establish that
it contains every matching Opportunity.

A capped list is appropriate for a morning briefing. The defect is presenting a possibly capped
row count or amount as though it represents the complete matching population.

## Reproduction — reproduced

### Minimum setup

In a non-production test org, use a dedicated test account and create 51 Opportunities owned by
the current user. Set every record to an open stage, give each a past-due `CloseDate`, and set each
`Amount` to `$1,000`.

### Detail-query action

Run the upstream past-due detail-query shape below. The field selection is reduced to the fields
needed to demonstrate the result; the `scope`, predicate, cap, and ordering match the affected
skill.

```graphql
query {
  uiapi {
    query {
      Opportunity(
        scope: MINE
        where: {
          IsClosed: { eq: false }
          CloseDate: { lt: { literal: TODAY } }
        }
        first: 50
        orderBy: { CloseDate: { order: ASC } }
      ) {
        edges {
          node {
            Id
            Amount { value }
          }
        }
      }
    }
  }
}
```

It returns:

```text
returned rows: 50
visible-row amount sum: $50,000
```

To establish the complete population, run an equivalent aggregate for the current user with the
same open and past-due predicates:

```graphql
query {
  uiapi {
    aggregate {
      Opportunity(
        where: {
          OwnerId: { eq: "<current-user-id>" }
          IsClosed: { eq: false }
          CloseDate: { lt: { literal: TODAY } }
        }
      ) {
        edges {
          node {
            aggregate {
              Id { count { value } }
              Amount { sum { value } }
            }
          }
        }
        totalCount
      }
    }
  }
}
```

It returns:

```text
totalCount: 51
Id.count: 51
Amount.sum: $51,000
```

## Observed and expected behavior

**Observed:** the bounded detail response exposes only 50 rows and `$50,000`, while the matching
population contains 51 rows and `$51,000`. Without aggregate or pagination data, the detail
response cannot show whether the visible rows are complete.

**Expected:** when labels make population-level count or dollar claims, they should use
aggregate-backed values and disclose truncation, for example `showing 50 of 51 · $51,000 total`.
If aggregate data is unavailable, the output should describe the data as a bounded list and not
represent the visible-row count or sum as the whole population.

## Affected output contract

The widget binds `closingLabel` and `pastDueLabel` as count-and-dollar labels above capped
datagrids. The fallback also includes:

```text
## Closing in 14 Days ([N] opps, $[total])
```

These forms read as population totals rather than an explicitly bounded slice.

## Narrow proposed upstream fix

Keep the current `first: 50` detail roots. Add aggregate roots in the same GraphQL dispatch for
closing-soon and past-due, representing the same Opportunity population as each corresponding
detail root.

- Use `Id.count` and `Amount.sum` for population-level count and dollar labels.
- When the aggregate count exceeds returned detail rows, say `showing R of C` or `Top 50 of C`.
- If aggregate data fails, use bounded-list wording instead of deriving a population total from
the capped visible rows.

This preserves the briefing's bounded-detail design while making aggregate-style claims accurate.
It does not change the active mirror.
