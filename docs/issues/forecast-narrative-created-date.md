# forecast-narrative: field-history read fails when `%QSTART%` is a date

- **Upstream issue:** [salesforce/salesforce-skills#15](https://github.com/salesforce/salesforce-skills/issues/15)
- **Status:** Open
- **Affected skill:** `salesforce-for-sales/skills/forecast-narrative/SKILL.md`

## Summary

The field-history fallback filters `OpportunityFieldHistory.CreatedDate` with `%QSTART%`, while the skill defines `%QSTART%` as a `YYYY-MM-DD` date. `CreatedDate` is a date-time field, so Salesforce rejects the query and the forecast-movement section can be omitted when no prior snapshot is supplied.

## Error

```text
INVALID_FIELD: value of filter criterion for field 'CreatedDate' must be of type dateTime
and should not be enclosed in quotes
```

## Reproduction

Fill `%QSTART%` with `2026-07-01` in the skill's `GET /services/data/v63.0/query` call. The field-history query fails because the filter is a date rather than a date-time literal.

## Proposed fix

Append midnight UTC in this one field-history filter:

```sql
WHERE CreatedDate >= %QSTART%T00:00:00Z
  AND Field IN ('StageName','Amount','CloseDate')
```

`%QSTART%` remains a `YYYY-MM-DD` value, so the skill's date-only `CloseDate` filters remain unchanged. The portable `forecast-narrative` skill contains this fix.
