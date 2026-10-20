# customer-health: Support counts come from a ten-row Case sample

- **Status:** Submitted upstream as [#21](https://github.com/salesforce/salesforce-skills/issues/21). Reproduced in a non-production test org.
- **Affected skill:** [`salesforce-for-sales/skills/customer-health/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/customer-health/SKILL.md)
- **Active mirror status:** Locally corrected in `agent-plugin/skills/customer-health/SKILL.md` and validated in Quick with synthetic data; the upstream source remains unchanged.

## Summary

The deep account read returns at most ten Cases:

```graphql
Cases(first: 10, where: { CreatedDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { CreatedDate: { order: DESC } })
```

Step 2 calls these "recent cases," but Step 3 scores the Support dimension from "open Cases,
aging/priority from step 2," and the widget contract asks for current values such as `18 open`.
The read returns no total or open count, so for any account with more than ten Cases in the window,
Support can reflect only the ten most recent Cases. Nothing in the instructions tells the host that
those rows are a capped sample.

## Reproduction — reproduced

### Minimum setup

In a non-production test org, create one account with more than ten Cases created in the last 90
days, most of them closed. The test account had 118 Cases in the window: 13 open, 3 in `Escalated`
status, and 89 with `High` or `Critical` priority.

### Current action and observed result

Run the skill's deep read. The `Cases` child returns exactly ten rows: 1 open, 1 escalated, and 9
High or Critical. A host following the skill rendered Support as ten cases in 90 days, with one
escalated and the rest closed.

### Complete counts for the same account and window

The same account predicate and window, read as aggregates:

```graphql
aggregate {
  Case(where: {
    Account: { Name: { like: "<account>" } },
    CreatedDate: { gte: { literal: LAST_90_DAYS } }
  }) {
    edges { node { aggregate { Id { count { value } } } } }
  }
}
```

| Last 90 days | Ten-row sample | Complete count |
|---|---:|---:|
| Cases | 10 | 118 |
| Open | 1 | 13 |
| Escalated status | 1 | 3 |
| High or Critical priority | 9 | 89 |

## Expected behavior

Support counts reflect every Case in the window. Detail rows can stay capped, but any output derived
from them should describe them as the most recent ten, not as the account's case population.

## Narrow proposed upstream fix

1. Add an `aggregate` block as a sibling of `query` in the same deep-read dispatch, using the same
   account predicate and 90-day window, for total and open Case counts. Escalated and high-priority
   counts can use the org's own status and priority values in the same way.
2. Take Support counts from those aggregates, and describe status or priority read from the rows as
   the latest ten.
3. Because the read selects the account with a name `like` filter and `first: 1`, also count the
   matching Accounts. If more than one matches, rerun with the exact-Id filter so the totals belong
   to the displayed account.

Adding these roots to the existing deep read executed as one request in the test org, and both the
name and exact-Id forms returned the complete counts above.

`Tasks(first: 20)` and `Opportunities(first: 20)` use the same unlabeled cap; this report reproduces
only the Case undercount. #18 reports the same capped-row pattern in `daily-briefing`.
