# Skill Eval Harness

A test harness for the skills in this Agent Plugin. It answers one question with a
scorecard instead of a vibe: **did a change to a skill actually make it better, or just
different?**

It follows the emerging standard for evaluating agent skills: define what "success" means,
capture a run, score it against a small set of checks, and compare over time. An eval is
**a prompt → a captured run (trace + artifacts) → a set of checks → a comparable score.**

> Sources: [OpenAI — Testing Agent Skills with Evals](https://developers.openai.com/blog/eval-skills),
> [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents),
> [LangChain — Evaluating Skills](https://www.langchain.com/blog/evaluating-skills),
> [AWS — Evaluate skill-equipped agents with Strands Evals + AgentCore](https://aws.amazon.com/blogs/machine-learning/evaluate-skill-equipped-agents-with-strands-evals-and-amazon-bedrock-agentcore/).
> Content rephrased for compliance with licensing restrictions.

## What we measure (four goal types)

The 31 workflow `eval.yaml` files are organized around these axes. The utility skills
`configure`, `update`, and `using-display-widget` are part of the 34-skill mirror but do not
have workflow eval specs.

| Goal | Question | Where it lives |
|---|---|---|
| **Outcome** | Did the task complete and is the final artifact correct? | `output_must_contain`, `output_must_link_records`, `rubric` |
| **Process (trajectory)** | Did the skill trigger, and did it call the intended reads/steps? | `should_trigger`, `expected_reads`, `batched_in_one_turn` |
| **Style** | Does the output follow the required conventions? | `rubric` |
| **Efficiency** | Did it get there without thrashing? | `efficiency` |

Two things get special weight because they're this plugin's failure modes:
- **Trigger/discovery** — a skill only helps if its `name` + `description` cause it to
  activate. `should_trigger` / `should_not_trigger` test routing.
- **Consent posture** — read-only skills must not write; draft-only skills must never send.
  This is enforced statically today (Layer A) and at runtime (Layer B `safety`).

## Two layers

### Layer A — static validator (runnable now, no org, no LLM, no deps)

`validate.py` runs deterministic checks over every `skills/<name>/SKILL.md`. It's fast,
free, and gates CI (non-zero exit on any BLOCKER).

```bash
python3 evals/validate.py                 # all skills
python3 evals/validate.py daily-briefing  # one skill
python3 evals/validate.py --json          # machine-readable
```

Checks (BLOCKER fails the build; WARNING is reported):

- **BLOCKER** — frontmatter `name` present, matches the Agent Skills name rule, ≤ 64 chars,
  and equals the directory name.
- **BLOCKER** — frontmatter `description` present.
- **BLOCKER** — every Salesforce call parses: each `dispatch_readonly` call's `queryInput`
  decodes to `{"query": "..."}` and the query's `()`, `[]`, `{}` balance and nest correctly
  (string literals ignored); SOQL `q` parentheses balance. The failure names the line. Added
  after the first conversion dropped closing braces in 11 queries.
- **BLOCKER** — consent posture holds: a `read-only` skill contains no write/send verbs; a
  `draft-only` skill contains an explicit never-send contract.
- **WARNING** — `description` ≤ 1024 chars and reasonably descriptive; `SKILL.md` ≤ 500
  lines.

### Layer B — runtime evals (partially built; runs against a live org)

Layer B validates behavior against a real org. It splits into a part we can run with just
the Salesforce CLI (read connectivity) and a part that needs the agent host (Quick/Claude).

#### Built now: live read-connectivity (`run_reads.py`)

`run_reads.py` executes each skill's `reads/*.graphql` fixtures against a connected org and
scores whether each read reached the org, returned valid GraphQL with no `errors`, and
returned rows (grounding queries are exempt from the row check, they return field
metadata). This proves the portable GraphQL contract works end-to-end on live data.

```bash
python3 evals/run_reads.py --org genwatt-demo            # all skills with reads/
python3 evals/run_reads.py --org genwatt-demo call-prep  # one skill
python3 evals/run_reads.py --org genwatt-demo --json     # machine-readable
```

- **`--org` is required** — pass an `sf` org alias. Use an org with **synthetic/sandbox
  data** (e.g. `genwatt-demo`), never production. Confirm what's connected with `sf org list`.
- **Read-only by construction.** The runner only issues `sf api request graphql` (reads).
  There is no write, create, update, delete, deploy, or send path in it.
- Read fixtures live in `evals/skills/<name>/reads/*.graphql` as **bare GraphQL** (not JSON-wrapped)
  and use standard fields so they run without org-specific custom grounding. Files named
  `ground-*.graphql` are treated as metadata grounding (no row expectation).

Verified current run against `genwatt-demo`: every checked fixture reached the synthetic org
and returned valid data. This remains a fixture-connectivity test; it does not prove agent
routing or final-output quality.

#### Built now: the skills' own calls (`e2e_calls.py`)

`run_reads.py` runs simplified GraphQL fixtures. `e2e_calls.py` runs every documented
`dispatch_readonly` call in `skills/*/SKILL.md` through the local MCP server (`local-mcp/`):
GraphQL, SOQL, and Configure's allowlisted Opportunity Full/View UI API layout GET. It therefore
tests the exact documented call shapes rather than only simplified fixture queries.

```bash
python3 evals/e2e_calls.py --org genwatt-demo                      # all skills
python3 evals/e2e_calls.py --org genwatt-demo forecast-narrative   # one skill
python3 evals/e2e_calls.py --list                                  # placeholders per call, no org
```

- Placeholders are filled with dummy values in the format the skill tells the model to use
  (ISO date-times in `calendar-events`, `YYYY-MM-DD` elsewhere, single-quoted Ids in SOQL).
  Configure's layout read uses an actual accessible Opportunity Id returned by its documented
  preceding lookup, or is reported as skipped when no Opportunity exists. A failure means the
  call breaks when filled as instructed. If a new placeholder appears, add it to `FILL` (or
  `SKILL_FILL` when one skill uses a shared name differently); unfilled ones are reported as
  `GAP`.
- It first checks that the server rejects a POST, a non-query endpoint, a GraphQL mutation,
  non-SELECT SOQL, and malformed UI API layout requests. Read-only throughout.
- Current verified run on the synthetic `fresh` org: **157 of 157 calls passed**, with no
  failures, unfilled placeholders, or skipped conditional reads. All six read-only guards
  passed. The active mirror carries twelve approved skill deviations: seven source corrections
  tracked by filed upstream issues and five Quick/Kiro adaptations:
  - `account-context`: preserve and safely rebuild its canonical deep query.
  - `account-tiering`: reconcile binary tier/heatmap thresholds and omit unavailable currency
    metrics rather than defaulting them to zero.
  - `lead-triage`: User and Group owner fragments ([#9](https://github.com/salesforce/salesforce-skills/issues/9)).
  - `forecast-narrative`: DateTime field-history boundary ([#15](https://github.com/salesforce/salesforce-skills/issues/15)).
  - `weekly-wrap`: two requests instead of one 12-root request ([#16](https://github.com/salesforce/salesforce-skills/issues/16)).
  - `calendar-events`: typed Opportunity grounding and no unsupported attendee metric in the
    active subtitle ([#20](https://github.com/salesforce/salesforce-skills/issues/20)).
  - `customer-health`: preserve and preflight the canonical deep Account query before its first
    Quick/Kiro dispatch, and take Support counts from aggregate case totals instead of the
    ten-row sample ([#21](https://github.com/salesforce/salesforce-skills/issues/21); source unchanged). It also shows the object-not-string widget
    payload example. Eight focused tests and the complete 70-test local suite pass; the
    query-preflight rule and case-total correction are Quick-validated, and the payload example
    has one clean Quick run, not yet enough to call it fixed.
  - `customer-voice`: take quotes only from docs and email with no Salesforce reads beyond the
    three scoping reads, and keep a zero-quote result on the output template with the period and
    at most one in-skill next step. Four focused tests pass, including a byte-for-byte check that
    the rules are the only difference from the source; a normal Quick rerun followed both rules.
  - `daily-briefing`: copy closing-soon and past-due row names from the returned values, using
    the Opportunity Name unchanged when it already begins with the Account Name. The calendar read
    also selects Event `AccountId` and passes it to the meeting-account read, so
    Opportunity-linked meetings resolve to their Account ([#22](https://github.com/salesforce/salesforce-skills/issues/22); source unchanged).
    When an email tool is available, the inbox checks run and their result is reported; otherwise
    the briefing says the inbox was not checked. Nine focused tests pass, including an exact
    source-plus-changes check. Quick reruns showed all three changes working.
  - `deal-advance-gap`: the step 2a name lookup searches open deals only, selects `totalCount`,
    and narrows once when the candidate list is cut off ([#23](https://github.com/salesforce/salesforce-skills/issues/23); source unchanged).
    Step 1 also returns the Stage picklist in the org's order, and the default target comes from it
    ([#24](https://github.com/salesforce/salesforce-skills/issues/24); source unchanged). Row states rest only on returned tasks and events, and unsourced exit
    criteria are labeled suggested steps; a widget self-check downgrades In motion or Scheduled rows
    that cannot name their task or event. Eleven focused tests pass, including an exact
    source-plus-changes check. Quick reruns showed all four changes working.
  - `deal-review`: the step 2 deal read selects `totalCount`. When several deals match, a
    documented candidate read, narrowed first by words from the request when more than 10 match,
    takes the one exact name match or the one open candidate, and otherwise asks which deal is
    meant without offering a cut-off list
    ([#26](https://github.com/salesforce/salesforce-skills/issues/26); source unchanged). Step 1
    also returns the Stage picklist in the org's order, and the stage tile takes its position and
    stages to close from it, the gap behind
    [#24](https://github.com/salesforce/salesforce-skills/issues/24)
    ([follow-up comment](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032)). Ten focused tests pass,
    including an exact source-plus-changes check. Neither correction has been run in Quick yet.
  - `deal-signals`: a book or team sweep returns the text digest instead of a widget that needs a
    score and trend no step computes, and a single-deal widget drops the chart-and-meter column
    ([#25](https://github.com/salesforce/salesforce-skills/issues/25); source unchanged). Stale commitment fires from the fetched
    `LastModifiedDate`, a skipped email search is stated, and the digest lists every flagged deal.
    Fourteen focused tests pass, including an exact source-plus-changes check and a schema check
    of the single-deal widget. Quick reruns showed the book-sweep, email, stale-commitment, and
    complete-digest rules working; the single-deal widget has not been run in Quick.

#### MCP Apps protocol, hosted contracts, and browser compatibility

`mcp_apps/` validates the widget-first `display_widget` path retained by the active skills:

- 25/26 active widget blocks match upstream exactly; `calendar-events` has one tightly checked
  variable-contract subtitle correction while its renderer JSON remains identical to upstream.
- 26/26 hosted Headless 360 calls return the submitted widget in structured content and
  Salesforce UI metadata.
- 26/26 meaningful Ravelin widgets pass a compatible cross-origin Chrome host, including
  130/130 explicit semantic checks and 59/59 capture-only actions (39 messages, 20 links).

The browser action host never sends a message, opens a URL, or writes Salesforce data. The
official basic host and MCP Inspector retrieve the populated App result but currently stall
this Salesforce renderer in their opaque-origin sandbox path; the positive gate uses separate
host/renderer origins with `allow-same-origin`. This proves compatible-host behavior, not Quick
support. See [`mcp_apps/README.md`](mcp_apps/README.md).

#### Not built here: agent-host evals (needs Quick/Claude runtime)

The CLI can run a skill's queries, but only the agent runtime can decide to *trigger* a
skill and produce its assembled output. These dimensions stay in `eval.yaml` as the
host-run contract and are executed where an agent + org are both available:

1. **Trigger/routing** — `should_trigger` / `should_not_trigger`: did the right skill fire?
2. **Deterministic output checks** — `output_must_contain`, records linked, and `safety`
   upheld (draft created, **nothing sent**, no Salesforce write). Note the email
   draft/never-send path can't be exercised by `run_reads.py` (no email connector, and it
   would be a write) — it's validated statically by Layer A and at the host at runtime.
3. **LLM-as-judge rubric** — the `rubric[]` criteria graded by a judge model (grounding, no
   fabrication, human labels, stage-appropriateness). The judge itself is built (see
   "LLM judge" below) and runs offline today; in Quick it grades the host's real outputs.
4. **Pairwise A/B** — old Claude skill vs. new portable skill on the same prompts, judge
   blind to which version it saw, with position-swap debiasing. Proves an edit helped
   rather than just changed behavior.

An AWS-native option for the host-run tiers is Strands Evals + Bedrock AgentCore (linked
above), which fits the Amazon Quick target.

#### Planned email-path eval (`email_eval` — requires a Quick host run)

The draft/send workflow specs (`draft-outreach`, `call-follow-up`, and `inbox-sweep`) carry an
`email_eval` contract. It has not been executed in Quick in this repository. When a Quick email
connector is available, the intended rules are:

- **Connector-gated.** If no email connector is available, the email checks report
  **SKIPPED**, not FAIL (the connector is optional; the skill must degrade to returning the
  subject+body as text).
- **Default assertion is capture-only, never delivery.** With a connector present, the eval
  checks that the skill **staged a draft** (To/Subject/Body present) and did **not** deliver
  it, and that the skill never auto-sends.
- **A real send is OFF by default.** `send_test.enabled: false`. Turning it on requires an
  explicit operator opt-in *and* an allowlisted recipient. Sends to any address not on the
  allowlist, or to addresses pulled from CRM data, fail the eval. This keeps the never-
  auto-send safety contract intact even when the send path is under test.

In short: this contract is designed to exercise the email path in Quick, but no Quick run has
been verified here. A genuine outbound send remains a deliberate, approved, allowlisted step—
never an unattended eval action.

### LLM judge (`judge.py`, `generate.py`)

Grades a skill's output against its `rubric[]`. Built and calibrated; runs on Bedrock.

```bash
# 1. produce an output offline: live org reads -> evidence -> executor model -> deliverable
python3 evals/generate.py --skill daily-briefing --org genwatt-demo
# 2. grade it (evidence defaults to the .evidence.json next to the output)
python3 evals/judge.py --skill daily-briefing --output evals/outputs/daily-briefing/live.md --samples 3
# prove the judge still catches planted defects (run after any judge-prompt change)
python3 evals/judge.py --calibrate evals/calibration/daily-briefing --samples 3
# inspect prompts without a model call
python3 evals/judge.py --skill daily-briefing --output X.md --print-prompt
python3 evals/generate.py --skill daily-briefing --org genwatt-demo --print-prompt
```

**How it grades.** Deterministic checks first (`output_must_contain`, record links, no raw
`__c` names, no leftover template tokens). Then each rubric criterion gets its **own** model
call with the skill's `SKILL.md`, the evidence, code-computed facts (exact row counts and
`Amount` sums per read), and the output. The judge must return each violation as a quote plus
reason. Code enforces the rest: a quote that isn't in the output is dropped, a violation the
judge marks as belonging to another criterion doesn't count, and the verdict is FAIL only if a
verified in-scope violation remains. `--samples N` takes a majority vote (ties go to FAIL).
Exit codes: 0 PASS, 1 FAIL, 2 error.

**Historical calibration.** The `daily-briefing` calibration previously scored 7/7 with three
samples each, but it has not been re-baselined against the current upstream-mirror reset. Do not
use that historical result as a current release gate until it is rerun. Its design remains:
- The executor never sees the rubric, and the judge never sees how the output was made.
- Calibration fixtures in `calibration/<skill>/` pair one correct output with bad outputs that
  each plant exactly one defect class. `expected.json` says which criteria must FAIL and which
  must PASS, so a judge that fails the wrong criterion (scope bleed) is caught too. The
  `daily-briefing` set (good, bad-fabrication, bad-blank, bad-labels, bad-totals,
  good-truncated, bad-rowsum) scores 7/7 with 3 samples each, unanimous on every criterion.
- Models are unreliable at adding long columns. Early testing found a live briefing total off
  by $57,000. Code-computed facts and aggregate fixtures exist to catch that class of error;
  their applicability must be confirmed when the judge calibration is re-baselined.

**Credentials and data flow.** Defaults: AWS profile `agentforce-demo`, region `us-east-1`,
model `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Override with `--profile/--model/--region`
or `EVAL_AWS_PROFILE`, `EVAL_MODEL`, `EVAL_AWS_REGION`. Any profile whose name contains `prod`
is refused before a request is sent. Calls go through the AWS CLI (`aws bedrock-runtime
converse`), so there's no Python dependency. The model receives `SKILL.md`, the org evidence,
and the output. Only use orgs with synthetic data. Generated outputs land in `evals/outputs/`
(git-ignored).

**Limits.** `generate.py` isn't the Quick runtime. It tests SKILL.md instructions plus real
data turned into a deliverable, not trigger/routing. Non-Salesforce connectors are reported to
the executor as unavailable. A skill's live output is only as complete as its `reads/`
fixtures (for example, `daily-briefing/reads/` has no Event or currentUser read yet, so the
live briefing has no meetings section). Aggregate reads (`reads/*-total.graphql`) show as
`aggregate` in `run_reads.py` and are checked for a returned value instead of rows. Calibration only exists for `daily-briefing` so far.

## `eval.yaml` schema

There are 31 workflow specs under `evals/skills/<name>/eval.yaml`. Layer A reads only
`posture`; the rest is the Layer B contract. The three utility skills (`configure`, `update`,
`using-display-widget`) intentionally have no workflow spec.

**Eval files never go in the skill folder.** Everything under `skills/<name>/` ships with the
skill when it's installed, and the Agent Plugins spec has no ignore file. So the harness keeps
its files under `evals/`:

```
skills/<name>/SKILL.md               # shipped
evals/skills/<name>/eval.yaml        # eval-only
evals/skills/<name>/reads/*.graphql  # eval-only
evals/calibration/<name>/            # eval-only
```

This matters because the read fixtures differ from the skill's own queries: they drop
`scope: MINE` and custom fields so they run on any org. An agent that found and ran them
would read org-wide data. `validate.py` enforces the layout with a BLOCKER check.

```yaml
skill: <name>                    # must match the directory / frontmatter name
posture: read-only | draft-only | write   # drives Layer A consent checks

should_trigger:                  # prompts that SHOULD activate this skill
  - "..."
should_not_trigger:              # prompts that belong to a neighbor skill
  - "..."

expected_reads:                  # substrings that should appear in the issued Salesforce reads
  - "..."
batched_in_one_turn: true|false  # steps the skill says to issue together
forbidden_endpoints: ["discover", "describe"]

output_must_contain:             # deterministic substring checks on the final Markdown
  - "..."
output_must_link_records: true|false   # SF records linked as /lightning/r/<Type>/<Id>/view

safety:                          # draft-only / write skills only
  must_create_draft_only: true
  must_not_send: true
  must_not_write_salesforce: true

rubric:                          # natural-language criteria for the LLM judge
  - "..."

efficiency:
  no_repeated_identical_reads: true
  max_salesforce_reads: <int>
```

## Adding an eval for a new skill

1. Mirror the upstream skill per `../CONVERSION_RECIPE.md`; do not rewrite or remove its widget.
2. Add `evals/skills/<name>/eval.yaml`, at minimum a correct `posture` (so Layer A can enforce
   consent) plus `should_trigger` and a short `rubric`.
3. Run `python3 evals/validate.py <name>` until it's clean.
4. Add `evals/skills/<name>/reads/*.graphql` fixtures (bare GraphQL, standard fields) for the
   skill's key reads, and run `python3 evals/run_reads.py --org <sandbox> <name>`.
5. When a Quick agent is available, run the host-run tiers against `should_trigger` and
   grade with the `rubric`.

## CI

Wire Layer A as a gate (fails on any blocker):

```bash
python3 agent-plugin/evals/validate.py
```

Run it on every change to a `SKILL.md` — it needs no org, no network, no LLM.

Where a sandbox org is reachable, add the read-connectivity gate:

```bash
python3 agent-plugin/evals/run_reads.py --org <sandbox-alias>
```

The remaining host-run tiers (trigger/routing, output rubric, pairwise A/B) run where an
agent + org are both available — locally, or in a pipeline stage that can reach them.
