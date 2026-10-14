# weekly-wrap: step 2 read exceeds GraphQL 10-subquery limit (12 roots), always fails

- **Upstream issue:** [salesforce/salesforce-skills#16](https://github.com/salesforce/salesforce-skills/issues/16)
- **Status:** Open

**Skill:** `weekly-wrap` (1.0.0-beta.2.3)

**What happens**

The step 2 read sends six `query {}` roots and six `aggregate {}` roots in one GraphQL request. Salesforce rejects it before running any of it:

```
{"data":{},"errors":[{"extensions":{"ErrorType":"ExecutionAborted"},"message":"The number of data fetchers in the query is 12, exceed the data fetcher limitation 10. Please simplify the ..."}]}
```

GraphQL API allows up to 10 subqueries per request ([query limits](https://developer.salesforce.com/docs/platform/graphql/guide/query-limits.html)). So this call fails every time, in any org, with no data returned. The skill's fallbacks only handle a grouping `DataFetchingException`, so the agent has nothing to recover with.

**Repro**

Send the step 2 call as written, with `<OPP_CUSTOM>` empty and `scope: MINE`. I tried it on `/services/data/v60.0` through `v68.0`. All fail with `data fetchers ... is 12`. It fails the same way through the hosted Headless 360 MCP server's `dispatch_readonly` (from Kiro, Developer Edition org), and when sent straight to the org's `/graphql` endpoint with the `sf` CLI.

**What works**

Split the request into two dispatches in the same turn: the six detail roots in one request and the six aggregate roots in the other. Both return data. (The existing "drop the two grouped roots" fallback has 10 roots and also succeeds, but it only runs after a grouping error.)

**Suggested fix**

- Make step 2 two dispatches (detail, then aggregate) and update the "one dispatch" wording.
- With the split, a grouped-root `DataFetchingException` only takes down the aggregate request, so the whole-request fallback can just re-fire the aggregate request without `closedAgg` and `touchedAgg`.
