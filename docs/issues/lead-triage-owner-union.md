# lead-triage: Lead read fails with `FieldUndefined` on `Lead_Owner.Name`

- **Upstream issue:** [salesforce/salesforce-skills#9](https://github.com/salesforce/salesforce-skills/issues/9)
- **Status:** Open
- **Affected skill:** `salesforce-for-sales/skills/lead-triage/SKILL.md`

## Summary

The step-2 Lead query selects `Owner { Name { value } }`. Salesforce GraphQL treats `Lead.Owner` as the polymorphic `Lead_Owner` union, which has no shared `Name` field. As a result, the read fails validation before returning the lead.

## Error

```text
Validation error (FieldUndefined@[uiapi/query/Lead/edges/node/Owner/Name]):
Field 'Name' in type 'Lead_Owner' is undefined
```

## Reproduction

The issue is reproduced by posting the skill's Lead GraphQL query with its placeholders filled. It was confirmed on API versions v60.0 through v67.0 in a Developer Edition org.

## Proposed fix

Select through explicit polymorphic fragments:

```graphql
Owner {
  ... on User { Name { value } }
  ... on Group { Name { value } }
}
```

This supports both user-owned and queue-owned Leads. The portable `lead-triage` skill contains this fix.
