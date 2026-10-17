# Active upstream skill mirror

This directory mirrors all 34 skills in `salesforce-for-sales/skills/`. Each active skill
preserves the complete upstream content, including Headless 360 calls, widget-first
`display_widget` instructions, renderer and variable contracts, and the source text fallback.

Only three deviations from upstream are allowed:

| Skill | Issue | Necessary change |
|---|---|---|
| `lead-triage` | [#9](https://github.com/salesforce/salesforce-skills/issues/9) | Select both User and Group owner fragments so queue-owned leads resolve. |
| `forecast-narrative` | [#15](https://github.com/salesforce/salesforce-skills/issues/15) | Use a UTC DateTime boundary for `OpportunityFieldHistory.CreatedDate`. |
| `weekly-wrap` | [#16](https://github.com/salesforce/salesforce-skills/issues/16) | Split the 12-root GraphQL read into two dispatches to stay below the 10-fetcher limit. |

All other skill files must remain byte-for-byte equal to upstream. See
[`../CONVERSION_RECIPE.md`](../CONVERSION_RECIPE.md) for the synchronization policy and
[`../../docs/portable-skill-diff-report.md`](../../docs/portable-skill-diff-report.md) for the
current comparison.
