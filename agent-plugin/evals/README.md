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

Every skill's `eval.yaml` is organized around these axes:

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
- **BLOCKER** — no forbidden tokens in the body: `display_widget`, `dispatch(`, `discover(`,
  `describe(` (the Claude widget, the Headless 360 write tool, and its discovery tools).
  Reads through `dispatch_readonly(` are allowed.
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

Verified run against `genwatt-demo`: all fixtures for `daily-briefing`, `call-prep`, and
`draft-outreach` returned valid data (e.g. closing-soon 13 rows, past-due 40 rows).

#### Built now: the skills' own calls (`e2e_calls.py`)

`run_reads.py` runs simplified fixtures. `e2e_calls.py` runs every `dispatch_readonly` call in
`skills/*/SKILL.md` as written, through the local MCP server (`local-mcp/`), so it tests the
exact text the agent will send.

```bash
python3 evals/e2e_calls.py --org genwatt-demo                      # all skills
python3 evals/e2e_calls.py --org genwatt-demo forecast-narrative   # one skill
python3 evals/e2e_calls.py --list                                  # placeholders per call, no org
```

- Placeholders are filled with dummy values in the format the skill tells the model to use
  (ISO date-times in `calendar-events`, `YYYY-MM-DD` elsewhere, single-quoted Ids in SOQL).
  A failure means the call breaks when filled as instructed. If a new placeholder appears, add
  it to `FILL` (or `SKILL_FILL` when one skill uses a shared name differently); unfilled ones
  are reported as `GAP`.
- It first checks that the server rejects a POST, a non-query endpoint, a GraphQL mutation, and
  non-SELECT SOQL. Read-only throughout.
- Last run on `genwatt-demo` (after the upstream 1.0.0-beta.2.3 merge): 148 of 148 calls ok.
  It found two bugs that are also present upstream:
  - `forecast-narrative` `CreatedDate`: a date filled into a date-time filter.
  - `weekly-wrap`: 12 roots in one GraphQL request, above the 10-subquery limit. We split it
    into two dispatches.

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

#### Email-path eval (`email_eval` — runs in Quick)

Draft/send skills (`draft-outreach`, and once converted `call-follow-up`, `inbox-sweep`)
carry an `email_eval` block in their `eval.yaml`. The email connector lives in **Quick**,
so this tier runs there, not in `run_reads.py`. Its rules:

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

In short: running these evals in Quick exercises the email path for real, but a genuine
outbound send only happens as a deliberate, approved, allowlisted step — never as an
unattended eval action.

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

**How it stays honest.**
- The executor never sees the rubric, and the judge never sees how the output was made.
- Calibration fixtures in `calibration/<skill>/` pair one correct output with bad outputs that
  each plant exactly one defect class. `expected.json` says which criteria must FAIL and which
  must PASS, so a judge that fails the wrong criterion (scope bleed) is caught too. The
  `daily-briefing` set (good, bad-fabrication, bad-blank, bad-labels, bad-totals,
  good-truncated, bad-rowsum) scores 7/7 with 3 samples each, unanimous on every criterion.
- Models are unreliable at adding long columns. Early on the judge passed a live briefing
  whose 13-row total was off by $57,000. That's why the computed facts exist, and why
  `bad-totals` is in the calibration set. The skill itself now gets totals from Salesforce
  aggregate reads (see `CONVERSION_RECIPE.md`), and the computed facts include those aggregate
  values, so a total that matches Salesforce passes even when it exceeds the visible rows
  (`good-truncated`) and a total summed from visible rows fails (`bad-rowsum`).

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

One `eval.yaml` per skill at `evals/skills/<name>/eval.yaml`. Layer A reads only `posture`;
the rest is the Layer B contract.

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

1. Convert the skill per `../CONVERSION_RECIPE.md`.
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
