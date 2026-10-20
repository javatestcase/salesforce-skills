# deal-review: a short name match can silently review a different deal

- **Upstream issue:** [salesforce/salesforce-skills#26](https://github.com/salesforce/salesforce-skills/issues/26)
- **Status:** Open
- **Affected skill:** [`salesforce-for-sales/skills/deal-review/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/deal-review/SKILL.md)
- **Active mirror status:** Applied locally as an approved temporary deviation. The upstream
  source is unchanged.

## Summary

Step 2 finds the deal and reads its details in one query: it matches `%DEALNAME%` (1–2 words),
sorts by `CloseDate` descending, and takes `first: 1`. The skill says this ordering favors the
current deal when a name matches several records, and it falls back to a resolver only when the
result is empty.

When different deals share the words, the query returns whichever has the latest close date, and
nothing in the response shows that other deals matched. The skill then reviews that deal without
any check or question.

## Reproduction — reproduced

### Minimum setup

In a non-production test org, create two open Opportunities whose names share a phrase, for
example "Phase 1" and "Phase 2" of the same project. Give the one the user will ask about the
earlier close date.

### Current read

Run step 2 as written, with `%DEALNAME%` set to the shared phrase. The selection below is reduced
to the relevant fields; the filter, ordering, and cap match the skill.

```graphql
query {
  uiapi {
    query {
      Opportunity(
        where: { Name: { like: "%<phrase>%" } }
        orderBy: { CloseDate: { order: DESC } }
        first: 1
      ) {
        edges { node { Id Name { value } CloseDate { value } } }
      }
    }
  }
}
```

It returns only the later-closing deal ("Phase 2"). Followed as written, the skill reviews
"Phase 2" when the user asked about "Phase 1".

In a larger synthetic org, the same read for an account's $1.3M deal returned a different deal
depending on which words filled `%DEALNAME%`. The match counts come from the `totalCount` read in
the next section.

| `%DEALNAME%` | Matches | Deal returned |
|---|---:|---|
| The last two words of the deal name | 78 | A $21K deal on a different rep's account |
| The account name | 14 | A different $836K deal on the same account |
| Two other words of the deal name | 34 | The requested deal, the latest-closing of the 34 |
| The full name | 1 | The requested deal |

### Same read with a match count

Adding `totalCount` to the same selection returns `totalCount: 2` in the minimum setup and the
counts in the table above. A short candidate read over the same phrase (`Id`, `Name`, `StageName`,
`CloseDate`, `IsClosed`, `Account.Name`, `first: 10`) then lists the matches, and the deal whose
name equals the one requested can be read by Id.

When more deals match than the candidate read returns, its list is cut off and can leave out the
requested deal. In the larger org, adding the account name from the request to the deal words
(`%<account>%<deal words>%`) cut both phrases that returned a different deal from 78 and 14
matches to 2: the requested deal and a closed deal on the same account. Names are not unique
either. Three deals in that org share one name, two of them open; a cut-off list for a two-word
phrase showed only one of them, while the narrowed list showed all three.

All reads used the Salesforce GraphQL API at v65.0, the version the skill uses. The step 2 and
candidate reads ran directly in two separate non-production orgs, one Developer Edition and one
Enterprise Edition, and through the skill's `dispatch_readonly` tool in the Enterprise Edition
org. The narrowed reads ran directly in the Developer Edition org.

## Observed and expected behavior

**Observed:** whether the review covers the requested deal depends on which words the agent picks
for `%DEALNAME%`, and a wrong pick produces a confident review of another deal with no warning.
Even a correct pick can depend on the requested deal closing last among many matches.

**Expected:** the review covers the requested deal, or the agent asks which deal is meant when the
name is ambiguous.

## Narrow proposed fix

- Select `totalCount` in the step 2 read.
- When it is above 1, run a short candidate read before using the result. When the count is above
  the candidate read's page size, first narrow the phrase with words from the request, such as the
  account name, never with a name from a returned deal.
- Take the one candidate whose name equals the requested deal, or else the one open candidate.
  Otherwise list the candidates and ask which is meant. If the list is still cut off, or the
  request gives nothing to narrow with, say how many deals matched and ask for the full name or
  the account instead of offering a partial list.
- Keep the step 2 result when it is the chosen deal; otherwise rerun the full read by Id, as the
  skill already does after its empty-result resolver.
- Leave the widget and the other steps unchanged.
