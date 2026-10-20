# deal-signals: widget needs a signal score and trend that no step computes

- **Upstream issue:** [salesforce/salesforce-skills#25](https://github.com/salesforce/salesforce-skills/issues/25)
- **Status:** Open
- **Affected skill:** [`salesforce-for-sales/skills/deal-signals/SKILL.md`](https://github.com/salesforce/salesforce-skills/blob/main/salesforce-for-sales/skills/deal-signals/SKILL.md)
- **Active mirror status:** Applied locally as an approved temporary deviation. The upstream
  source is unchanged.

## Summary

`deal-signals` builds a deal-risk digest for the rep's book. Step 2 reads up to 100 open
Opportunities, step 3 fires risk signals such as gone quiet, overdue, and danger zone, and the
step 5 text format groups the flagged deals under "Act today" and "This week". The global rules
make the widget the required output whenever `display_widget` is available.

The widget describes a different deliverable: one Opportunity's buying signals. Its header carries
a single deal's facts (`dealContext`) and link (`oppUrl`). Its two graphs are a 0–100 composite
signal score (`meterValue`, with Cold/Warm/Hot bands) and a six-week score trend (`chartSeries`).
Its rows are typed as buying signals with Buy/Watch status, and the template hard-codes success styling
for the status badge and the closing callout.

No step defines the composite score or reads any history to chart. The rules say to compute every
widget value from data already fetched and never invent one, and the pre-render check requires
both graphs to be present.

The widget has had this shape since the skill was first added, alongside a description and digest
format that have always covered the whole book.

## Reproduction — reproduced

### Minimum setup

A non-production test org where the current user owns accounts with several open Opportunities.

### Current reads

Run steps 1 and 2 as written. Step 2 returned 54 open Opportunities in one test org and 21 in
another. Each row carries only these fields, plus any confirmed custom fields:

```text
Id, Name, StageName, Amount, CloseDate, NextStep, LastActivityDate,
LastModifiedDate, ForecastCategory, Account.Name
```

None of them is a score, and no read returns weekly history.

### Widget requirements

| Widget values | Contract | Source in the skill |
|---|---|---|
| `meterValue`, `meterValueLabel` | Composite signal score, 0–100 | None |
| `chartCategories`, `chartSeries` | Six weekly score points | None |
| `dealContext`, `oppUrl` | One Opportunity's facts and link | Step 2 returns the whole book |

The skill's widget schema (`using-display-widget/widget-definition.schema.json`) requires
`categories`, `series`, and `caption` for `tile/chart`, and `value` and `valueLabel` for
`tile/meter`. Omitting those keys under the contract's "omit keys you have no data for" rule
therefore leaves incomplete tiles. The hosted `display_widget` tool accepted a widget built that
way, so the requirement is not enforced server-side; how the empty tiles render was not tested.

Both reads used the Salesforce GraphQL API at the versions the skill uses, in two separate
non-production orgs, one Developer Edition and one Enterprise Edition, both directly and through
the skill's `dispatch_readonly` tool.

## Observed and expected behavior

**Observed:** a host following the skill has to invent the score and trend, render one deal out of
the book, or skip the widget against the widget-first rule. In an agent run on a 21-deal book, the
agent returned the text digest without calling `display_widget`.

**Expected:** the required output can be built from the skill's own reads for its default scope,
without invented values.

## Narrow proposed fix

- For book and team sweeps, replace the widget with a multi-deal digest layout built only from the
  step 2 fields, such as one row per flagged deal with its signal, stage, amount, close date, last
  activity, and next step. If sweeps should not have a widget, make the step 5 digest the output
  instead.
- For a single deal, either define the composite score and the history behind its six-week trend,
  or drop the chart-and-meter column and the "two graphs present" check.
- Let the status badge and callout styling follow the signals instead of always showing success.
