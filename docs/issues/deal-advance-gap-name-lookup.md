# deal-advance-gap: name lookup can omit the deal the user named

- **Upstream issue:** [salesforce/salesforce-skills#23](https://github.com/salesforce/salesforce-skills/issues/23)
- **Status:** Open
- **Affected skill:** [`salesforce-for-sales/skills/deal-advance-gap/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/deal-advance-gap/SKILL.md)
- **Active mirror status:** Applied locally as an approved temporary deviation. The upstream
  source is unchanged.

## Summary

Step 2a resolves a deal name with a candidate query that matches 1–2 distinctive words, sorts by
`CloseDate` ascending, and returns the first 10 rows. It includes closed deals and requests no
total count.

When more than 10 Opportunities share the words, the oldest ones, usually closed, fill the list,
and the open deal the user named can fall outside it. Step 2a then says to list the candidates and
ask which one, so the user can be asked to choose among deals that do not include theirs. Nothing
in the response tells the agent that the list is incomplete.

## Reproduction — reproduced

### Minimum setup

In a non-production test org:

1. Create 11 closed Opportunities whose names contain the same two-word phrase, each with a past
   close date.
2. Create one open Opportunity whose name contains the same phrase, with a later close date.

### Current candidate query

Run the step 2a query as written, with `%DEALNAME%` set to the shared phrase. The selection below
is reduced to the relevant fields; the filter, ordering, and cap match the skill.

```graphql
query {
  uiapi {
    query {
      Opportunity(
        where: { Name: { like: "%<phrase>%" } }
        orderBy: { CloseDate: { order: ASC } }
        first: 10
      ) {
        edges {
          node {
            Id
            Name { value }
            StageName { value }
            CloseDate { value }
          }
        }
      }
    }
  }
}
```

It returns:

```text
rows: 10, all closed
open Opportunity: not returned
total count: not requested
```

Step 2a's "Several" branch then lists these 10 closed deals and asks the user which one they
meant. The deal they named is not offered.

In a larger synthetic org, a two-word phrase from a requested deal's name matched 78
Opportunities, 19 of them open. The first 10 by close date were all closed, and the requested open
deal was not among them.

### Same query with an open filter and total count

```graphql
Opportunity(
  where: { Name: { like: "%<phrase>%" }, IsClosed: { eq: false } }
  orderBy: { CloseDate: { order: ASC } }
  first: 10
) {
  totalCount
  edges {
    node {
      Id
      Name { value }
      StageName { value }
      CloseDate { value }
    }
  }
}
```

In the minimum setup, it returns the open Opportunity as the only candidate (`totalCount: 1`).
In the larger org, it returns 10 rows with `totalCount: 19`, which shows the list is cut off.
Adding the account name to the phrase then returns only the requested deal (`totalCount: 1`).

The minimum setup was reproduced in an Enterprise Edition org through the skill's
`dispatch_readonly` tool, and the larger case in a Developer Edition org through the GraphQL API
directly, both at v65.0.

## Observed and expected behavior

**Observed:** the candidate list can omit the named deal, and the agent cannot tell that it did.
Following step 2a then means asking the user to pick from wrong candidates. In an agent run on
the larger data set, the agent found the deal only by running its own narrower search, which the
skill does not document.

**Expected:** the named open deal appears among the candidates, or the agent knows the list is
cut off and narrows the search before asking.

## Narrow proposed fix

- Add `IsClosed: { eq: false }` to the step 2a filter. The skill is about advancing a deal, which
  a closed deal cannot do.
- Select `totalCount`. When it is greater than the rows returned, narrow `%DEALNAME%` (for
  example, with the account name) and retry once instead of asking the user to choose from a
  partial list.
- When the request names the account as well as the deal, include both in `%DEALNAME%`.
- Leave the detail read, widget, and other steps unchanged.
