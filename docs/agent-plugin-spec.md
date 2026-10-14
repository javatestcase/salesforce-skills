# Spec: Portable Salesforce Sales Skills (Agent Plugin)

| | |
|---|---|
| Status | Draft for review |
| Last updated | 2026-10-10 |
| Audience | Salesforce plugin owners, Amazon Quick, client teams adopting Agent Plugins |
| Package | `agent-plugin/` (`salesforce-for-sales` v2.0.0) |
| Source plugin | `salesforce-for-sales/` (Claude Code / Cowork, v1.0.0-beta.1.2), unchanged |

## 1. Summary

We rebuilt the `salesforce-for-sales` skills as a vendor-neutral [Agent Plugin (v1.0.0)](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md)
so one package runs in Amazon Quick, Kiro, and any other conformant client, instead of
porting to a single host's format. All 31 skills are converted, keep the original Salesforce
Headless 360 queries unchanged, and pass a static validator. Every Salesforce call in the
skills has been run read-only against a demo org with synthetic data.

The original Claude plugin is untouched. The portable package sits next to it.

This doc covers the design, the rules every converted skill follows, the safety model, how we
verify the skills, current status, and the open questions for Salesforce and Quick.

## 2. Background

The current plugin is a Claude Code marketplace: `.claude-plugin/` manifests, a `.mcp.json`
with Claude-specific fields, and skills that end by rendering a `display_widget` (a
Claude/Cowork UI capability). The skill instructions themselves are already
[Agent Skills](https://agentskills.io/specification) (`SKILL.md`), and their Salesforce reads
go over MCP. So the logic is portable. The packaging and the UI are not.

Agent Plugins standardizes the portable part: `plugin.json` + `skills/` + `mcp.json`, with
host-specific material confined to reverse-domain extension folders. Quick and Kiro both load
this format.

## 3. Goals and non-goals

Goals

1. One package that installs in Quick and other Agent Plugins clients with no host-specific
   fork of the skills.
2. Identical Salesforce behavior to the original: same queries, same API versions, same
   grounding and error-recovery paths.
3. No weakening of the consent model. Read-only skills stay read-only; draft skills never send.
4. A usable deliverable on every host. Markdown is the guaranteed output; rich UI is optional.
5. Repeatable verification: a reviewer can see whether a skill change made it better, not
   only different.

Non-goals

- Changing the original Claude plugin or its distribution.
- New skills or new Salesforce capabilities.
- Write paths to Salesforce. No skill writes records today, and this port adds none.
- Building the Quick visual layer in this phase (see section 10, Phase 3).

## 4. Design

### 4.1 Standards stack

| Layer | Standard | Role here |
|---|---|---|
| Instructions | Agent Skills (`SKILL.md`) | One folder per sales workflow |
| Connectivity | MCP | Salesforce Headless 360 and Slack as remote servers |
| Packaging | Agent Plugins v1.0.0 | `plugin.json` + `skills/` + `mcp.json` |
| Host extras | Reverse-domain extension | `com.salesforce.quick/` for Quick UI guidance |

Background notes on each standard are in [`docs/standards/`](./standards/README.md).

### 4.2 Package layout

```
agent-plugin/
├── plugin.json                 # closed manifest, $schema 1.0.0
├── mcp.json                    # salesforce-h360 + slack (streamable-http, HTTPS, no secrets)
├── skills/<name>/SKILL.md      # 31 skills; shipped
├── com.salesforce.quick/ui/    # Quick rich-UI guidance; ignored by other clients
├── SETUP.md                    # connector, auth, and read-only setup
├── CONVERSION_RECIPE.md        # the rules in section 5
└── evals/                      # validator, read fixtures, judge; never shipped inside skills/
```

`plugin.json` uses only fields the closed schema allows (`name`, `version`, `description`,
`author`, `homepage`, `repository`, `license: Apache-2.0`, `keywords`, `extensions`).
`mcp.json` declares the same two servers as the original `.mcp.json`:

| Server | URL |
|---|---|
| `salesforce-h360` | `https://api.salesforce.com/platform/mcp/v1/platform/headless-360` |
| `slack` | `https://mcp.slack.com/mcp` |

The spec forbids credentials in `mcp.json`, so the Headless 360 consumer key and Slack auth
are managed by the client (Quick connectors, Kiro OAuth), not the package.

### 4.3 What changed from the original and what didn't

| Original artifact | Portable package |
|---|---|
| `.claude-plugin/marketplace.json`, `plugin.json` | Replaced by root `plugin.json` |
| `.mcp.json` (with per-server `description`) | `mcp.json`; the tool-blocking guidance moved to `SETUP.md` because the format has no `description` field |
| `skills/*/SKILL.md` | Kept; edits listed in section 5 |
| Headless 360 calls | Unchanged, character for character |
| `display_widget` + widget JSON | Removed; the text fallback is now the primary output |
| `using-display-widget` skill | Retired from `skills/`; its content seeds `com.salesforce.quick/ui/` |
| `voice-profile` | Kept as a skill (it produces a deliverable) |

## 5. Skill conversion contract

Every converted skill follows six rules. Details and worked examples are in
[`agent-plugin/CONVERSION_RECIPE.md`](../agent-plugin/CONVERSION_RECIPE.md).

1. Frontmatter verbatim. `name` and `description` are copied exactly; `name` equals the
   folder name. No extra fields.
2. Global rules kept. The shared bootstrap block (connectivity check, grounding, citation,
   human labels, `scope: MINE` fail-fast, no `discover`/`describe`) is copied as-is, minus
   the widget-only rule, plus a short portability note.
3. Salesforce calls copied, not retyped. Calls stay in Headless 360 form, for example
   `dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql", queryParams: { "queryInput": "..." })`,
   with their pinned API versions (v63.0, v65.0, v66.0). Retyping the nested escapes dropped
   closing braces in 11 queries during the first pass, which is why copying is mandatory and
   the validator now parses every query.
4. Widget removed, text promoted. The Markdown deliverable becomes the primary output.
   Anything the widget showed that the text didn't (for example a past-due section) is
   folded into the text. Each skill ends with an optional pointer to the host UI layer.
5. Consent posture preserved (section 6).
6. Validated (section 8).

One addition beyond a straight port: totals come from Salesforce. Any skill that shows a
count or dollar total for a list issues a GraphQL `aggregate` read with the same `scope` and
`where` as the row read, in the same turn, and shows only that value. In testing the model
mis-added a 13-row list by $57,000, and row reads stop at `first: 50`, so model arithmetic
can be both wrong and incomplete. If the aggregate fails, the skill shows rows without a
total and says "showing N of M" when truncated.

## 6. Safety and consent model

### 6.1 Posture per skill

| Posture | Skills | Contract |
|---|---|---|
| Read-only (28) | all others | Never writes to Salesforce or sends anything |
| Draft-only (3) | `draft-outreach`, `call-follow-up`, `inbox-sweep` | Creates drafts; a human approves and sends. If the email connector can only send, the skill returns text instead |

Slack content is also draft-only until the user approves the exact message and channel.

### 6.2 Read-only enforcement, in layers

| Layer | Mechanism | Strength |
|---|---|---|
| Salesforce (primary) | Restrict the org's MCP server tools so only `dispatch_readonly` is allowed; permission set for users | Enforced server-side; the model can't bypass it |
| Client | Disable `discover`, `describe`, `dispatch`, `display_widget` (for example Kiro `disabledTools`) | Second layer; support for plugin-bundled servers varies by client |
| Skill text | Instructions to use only the listed `dispatch_readonly` calls | Instruction, not a control |
| Validator | Blocks `dispatch(`, `discover(`, `describe(`, `display_widget` tokens and checks posture wording | Catches regressions before merge |

Headless 360 tool settings we recommend:

| Tool | Setting |
|---|---|
| `dispatch_readonly` | allow |
| `discover`, `describe`, `dispatch` | block |
| `display_widget` | block (portable skills don't use it) |

### 6.3 Package hygiene

- No credentials in `mcp.json`, `headers`, or `env`. Remote URLs are HTTPS.
- Eval files (`eval.yaml`, read fixtures) never live inside `skills/`. Agent Plugins has no
  ignore file, so anything there ships. The fixtures drop `scope: MINE` to run on any org, and
  an agent that found them could read org-wide data. The validator blocks this layout.
- Testing uses only orgs with synthetic data. The LLM judge refuses any AWS profile whose name
  contains `prod`.

## 7. Host integration

| Host | How it loads | Salesforce access | Status |
|---|---|---|---|
| Amazon Quick | Agent Plugin portable core; ignores `mcp.json` | Quick console connectors; the model sends the same `url` and query through Quick's Salesforce read tool | Not yet tested |
| Kiro | Installs as a Power; loads `mcp.json` | Hosted Headless 360 (server defined in Kiro MCP settings with the ECA client ID), or a local read-only test server | Loads with all 31 skills; hosted Headless 360 sign-in not yet tested |
| Claude Code / Cowork | Original plugin, unchanged | Hosted Headless 360 | Unchanged |

Sign-in: the original setup puts the External Client App (ECA) consumer key in the MCP
config, but an Agent Plugins `streamable-http` entry allows only `type`, `url`, and `headers`,
so the package can't carry it. Public documentation settles most of this:

- No dynamic client registration. Salesforce's hosted MCP docs have an admin register an ECA,
  and each MCP server configuration links to one ECA
  ([client connection overview](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/client-connection-overview.html)).
  Third-party integration guides state that DCR isn't supported for hosted MCP
  ([MCP Manager](https://mcpmanager.zendesk.com/hc/en-us/articles/45499219300621-Setting-Up-Salesforce-Hosted-MCP-Servers-with-MCP-Manager),
  [Cargo](https://docs.getcargo.ai/integration/salesforce-mcp)). We found no first-party
  statement either way.
- Public PKCE clients are supported. Hosted MCP requires PKCE on every OAuth flow
  ([security best practices](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/security-best-practices.html)),
  and an ECA can turn off "Require secret for Web Server Flow" for clients that can't store a
  secret, as Salesforce documents for Data Loader
  ([ECA with PKCE](https://developer.salesforce.com/docs/platform/data-loader-impl/guide/loader-eca-oauth-pkce.html))
  and Mobile SDK.
- Localhost redirects are supported, with one catch. The hosted MCP ECA guide uses
  `http://localhost:<port>/callback` callbacks (for example Cursor's `http://localhost:8787/callback`)
  ([create an ECA](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/create-external-client-app.html)).
  An HTTP callback on `127.0.0.1` is reported to be rejected
  ([claude-code #86233](https://github.com/anthropics/claude-code/issues/86233)), so a client
  must redirect to `localhost`, not the loopback IP.

So every client needs the ECA consumer key configured outside the package: a Quick console
connector, or in Kiro a server defined in workspace or user MCP settings with `oauth.clientId`
(the plugin-bundled `salesforce-h360` entry can't authenticate on its own). Kiro supports
public clients only (PKCE, local redirect), which fits an ECA with the secret requirement off
and the `mcp_api` scope. Still to test: which exact redirect URI Kiro sends (`localhost` vs.
`127.0.0.1`, and port), so it can be registered on the ECA.

Content from external sources was rephrased for compliance with licensing restrictions.

Rich UI on Quick lives under `com.salesforce.quick/ui/`. It consumes the same assembled data
as the Markdown output and inherits the skill's posture: buttons on draft skills draft or
propose, never send or write without approval.

## 8. Verification

| Tier | Tool | Needs | What it proves |
|---|---|---|---|
| A. Static | `evals/validate.py` | Nothing (no org, network, or model) | Frontmatter, forbidden tokens, every query parses with balanced brackets, posture wording, eval files outside `skills/` |
| B1. Read fixtures | `evals/run_reads.py --org <sandbox>` | `sf` CLI + sandbox org | Each skill's key reads return valid GraphQL and rows on a live org |
| B2. Every call, end to end | Local MCP server (`evals/local-mcp/salesforce-readonly-mcp`) | `sf` CLI + sandbox org | Every `dispatch_readonly` call in every `SKILL.md`, sent through an MCP server with Headless 360's signature, executes |
| B3. Output quality | `evals/generate.py` + `evals/judge.py` | Sandbox org + Bedrock | Output graded against each skill's `rubric` by an LLM judge, with code-computed facts (row counts, aggregate totals) |
| C. Host-run | `eval.yaml` contract | Quick runtime + org | Trigger routing, deterministic output checks, email draft/never-send, pairwise A/B vs. original |

The local MCP server is a test tool, not part of the package. It exposes one tool,
`dispatch_readonly`, accepts only GET on the GraphQL and SOQL query endpoints, rejects GraphQL
mutations/subscriptions and non-SELECT SOQL before calling Salesforce, and leaves auth inside
`sf` so no access token passes through it.

The judge is kept honest by design: the executor never sees the rubric, the judge never sees
how the output was made, each violation must quote the output (code drops quotes that aren't
there), and a calibration set plants one known defect per bad sample so a judge that fails the
wrong criterion is caught.

Each skill has an `eval.yaml` declaring `posture`, `should_trigger` / `should_not_trigger`,
`expected_reads`, `output_must_contain`, `safety`, `rubric`, and `efficiency`. Draft skills
add an `email_eval` block: skipped when no email connector exists, asserts draft-created and
not-delivered when one does, and allows a real send only with operator opt-in to an
allowlisted, non-CRM recipient. Schema: [`agent-plugin/evals/README.md`](../agent-plugin/evals/README.md).

## 9. Current status

| Item | Result |
|---|---|
| Skills converted | 31 of 31 (30 workflows + `voice-profile`); `using-display-widget` retired to the Quick UI folder |
| Static validator | 31/31 PASS, 0 blockers, 0 warnings |
| Eval specs | 31 `eval.yaml`, 65 read fixtures |
| End-to-end calls (B2) | 143 of 147 calls succeed on a demo org with synthetic data; read-only guards 4/4 |
| Judge calibration | `daily-briefing` only: 7/7 calibration outputs graded correctly (3 samples each, unanimous) |
| Kiro | Installs as a Power; all 31 skills discovered |
| Quick | Not yet installed or run |
| Hosted Headless 360 from Kiro/Quick | Not yet tested. Auth path settled from public docs (section 7): pre-registered public PKCE ECA, no DCR |

The 4 failing calls trace to how the test harness fills placeholders, not to the queries
themselves. That's our read so far, and we haven't re-run them yet to confirm it:

| Skill | Cause | Follow-up |
|---|---|---|
| `calendar-events` | Harness used a date where `StartDateTime` needs an ISO datetime | Fix harness |
| `daily-briefing` | Harness didn't recognize the `<WhatId account 001…>` placeholder | Fix harness |
| `forecast-narrative` | SOQL `CreatedDate >= %QSTART%` needs a datetime literal; harness used a date | Fix harness; consider stating the literal format in the skill |
| `team-pipeline` | SOQL `IN (<TEAM_USER_IDS>)` needs single-quoted Ids; harness used double quotes | Fix harness; consider stating the quoting in the skill |

## 10. Roadmap

| Phase | Scope | State |
|---|---|---|
| 0 | Scaffold `plugin.json` / `mcp.json` | Done (Quick install check moves to Phase 3) |
| 1 | Convert 3 reference skills (`daily-briefing`, `call-prep`, `draft-outreach`); write the recipe | Done |
| 2 | Convert the remaining 28 skills; eval spec per skill | Done |
| 2.5 | Close verification gaps: re-run the 4 calls, move the end-to-end runner into `evals/`, add calibration sets beyond `daily-briefing`, test hosted Headless 360 auth | Next |
| 3 | Quick: install, map `dispatch_readonly` to Quick's connector, run host-run evals, build UI for widget-heavy skills (`daily-briefing`, `call-prep`, `draft-outreach`, `lead-triage`, `inbox-sweep`, `weekly-wrap`, `salesforce-hygiene-check`, pipeline views) | Planned |
| 4 | Distribution: publish in Quick's catalog; document install; keep the portable package as the source of truth | Planned |

## 11. Open questions

For Salesforce

1. Auth (mostly answered from public docs, section 7): there's no dynamic client registration,
   and a public PKCE ECA with an `http://localhost` callback is supported. Remaining asks:
   is DCR or Client ID Metadata Documents on the roadmap, so a portable package could
   authenticate without per-client setup? And will `127.0.0.1` loopback callbacks be
   accepted, since some MCP clients use the IP rather than `localhost`?
2. Read-only enforcement: is per-org (or per-permission-set) tool restriction to
   `dispatch_readonly` the recommended control? Could the server mark tools with MCP
   `readOnlyHint` / `destructiveHint` annotations so clients can enforce posture without
   per-client config?
3. Source of truth: two copies of 31 skills will drift. Options are (a) the portable package
   becomes the source and the Claude plugin adds its widget layer on top, (b) the reverse, or
   (c) generate one from the other. We lean toward (a). Related: keep `agent-plugin/` nested,
   or make the Agent Plugin the repo root?
4. API versions: skills pin v63.0 (14 SOQL calls), v65.0 (96), and v66.0 (37). We propose
   normalizing all 147 to v68.0 (Winter '27). On a Winter '27 demo org, every call returned
   the same result at v68.0, at v67.0, and at the current pins. The one risk is an org not yet
   upgraded to Winter '27, where `/v68.0` doesn't exist. Do you see any reason to stay on
   the older versions, or to pin v67.0 (the version the Headless 360 docs list) instead?
5. Posture review: we classed `salesforce-hygiene-check` as read-only because it proposes
   fixes but doesn't apply them. Please confirm.

For Amazon Quick

1. Confirm Quick installs the package as-is: loads `plugin.json` and `skills/`, ignores
   `mcp.json`, and can read `com.salesforce.quick/`.
2. How should skills address Quick's Salesforce connector? Today they name Headless 360's
   `dispatch_readonly` and rely on the model to route the same `url` and query through
   Quick's read tool. That mapping is untested.
3. Where should host-run evals (trigger routing, `email_eval`, A/B) execute? Strands Evals +
   Bedrock AgentCore is one candidate.

For the Agent Plugins spec

1. `mcp.json` has no per-server `description` and no per-tool allow/deny. Both would let a
   package declare its intended least-privilege tool set portably.

## 12. References

- [Agent Plugins v1.0.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md)
- [Agent Skills specification](https://agentskills.io/specification)
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Salesforce in Claude setup](https://help.salesforce.com/s/articleView?id=sales.what_is_salesforce_in_claude.htm&type=5)
- [Amazon Quick: Skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html)
- In repo: [`QUICK_MIGRATION_PLAN.md`](../QUICK_MIGRATION_PLAN.md), [`agent-plugin/SETUP.md`](../agent-plugin/SETUP.md),
  [`agent-plugin/CONVERSION_RECIPE.md`](../agent-plugin/CONVERSION_RECIPE.md),
  [`agent-plugin/evals/README.md`](../agent-plugin/evals/README.md), [`docs/standards/`](./standards/README.md)
