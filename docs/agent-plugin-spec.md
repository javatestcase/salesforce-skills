# Spec: Salesforce Sales Skills Agent Plugin

| | |
|---|---|
| Status | Implemented; Quick host integration remains unverified |
| Audience | Salesforce plugin owners and Agent Plugins client teams |
| Package | `agent-plugin/` (`salesforce-for-sales` v2.0.0) |
| Upstream source | `salesforce-for-sales/` |

## 1. Current design

`agent-plugin/` packages the Salesforce sales skills under the
[Agent Plugins v1.0.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md)
format. Its `skills/` directory is a mirror of all 34 upstream skills, not a Markdown-first
rewrite. It preserves full upstream content, including:

- Headless 360 `dispatch_readonly` calls and API versions;
- widget-first `display_widget` instructions;
- renderer JSON and variable-contract JSON, except the approved `calendar-events` subtitle
  correction;
- `using-display-widget`; and
- source text fallbacks.

Only twelve approved skill deviations differ from upstream: seven corrections tracked by filed upstream issues and five Quick/Kiro adaptations.

| Skill | Evidence | Change | Value |
|---|---|---|---|
| `account-context` | Synthetic Quick trace | Preserve and safely rebuild the canonical deep query. | Prevents malformed query reconstruction and aggregate relocation. |
| `account-tiering` | Synthetic Quick traces | Use the binary tier threshold in the heatmap and omit unavailable ARR/Whitespace values. | Visual totals reconcile and missing currency is never shown as zero. |
| `lead-triage` | [#9](https://github.com/salesforce/salesforce-skills/issues/9) | Add the Group fragment to `Lead.Owner`. | Queue-owned leads resolve and route correctly. |
| `forecast-narrative` | [#15](https://github.com/salesforce/salesforce-skills/issues/15) | Use `%QSTART%T00:00:00Z` for field-history `CreatedDate`. | Salesforce receives the required DateTime literal. |
| `weekly-wrap` | [#16](https://github.com/salesforce/salesforce-skills/issues/16) | Split six detail and six aggregate roots into two dispatches. | Both requests stay below the 10-fetcher limit. |
| `calendar-events` | [#20](https://github.com/salesforce/salesforce-skills/issues/20) | Query typed Opportunity facts and omit the unsupported attendee count. | Deal values/links are grounded and the subtitle does not misstate attendee data. |
| `customer-health` | Synthetic Quick trace; [#21](https://github.com/salesforce/salesforce-skills/issues/21) | Preserve and preflight the literal deep Account query, take Support counts from aggregate case totals, and show the object-not-string widget payload example. | No malformed first dispatch, and Support reflects every Case in the window. |
| `customer-voice` | Synthetic Quick trace | Take quotes only from docs and email with no extra Salesforce reads, and keep a zero-quote result on the output template. | A no-quote result reports no unscoped or capped Salesforce counts. |
| `daily-briefing` | Synthetic Quick trace; [#22](https://github.com/salesforce/salesforce-skills/issues/22) | Copy row names from the returned values, report the inbox check instead of dropping it, and resolve meetings through Event `AccountId`. | Row names match the queried records, the inbox result is always stated, and Opportunity-linked meetings resolve to their Account. |
| `deal-advance-gap` | Synthetic Quick traces; [#23](https://github.com/salesforce/salesforce-skills/issues/23); [#24](https://github.com/salesforce/salesforce-skills/issues/24) | Search open deals only and narrow a cut-off candidate list; take the target from the org's stage order; rest row states on returned activity; label unsourced exit criteria as suggested steps. | The named open deal is found, the target stage matches the org, and the checklist claims only what the data supports. |
| `deal-review` | Synthetic Quick trace; [#26](https://github.com/salesforce/salesforce-skills/issues/26); [#24 follow-up](https://github.com/salesforce/salesforce-skills/issues/24#issuecomment-6271505032) | Count the deal-read matches and resolve several through a documented candidate read, or ask; take the stage tile from the org's stage order. | The review covers the requested deal, and the stage tile matches the org. |
| `deal-signals` | Synthetic Quick trace; [#25](https://github.com/salesforce/salesforce-skills/issues/25) | Return the text digest for book and team sweeps and drop the score-and-trend column from a single-deal widget; flag stale next steps from `LastModifiedDate`; state a skipped email search; list every flagged deal. | No invented score or trend, stale next steps are caught, an unchecked inbox is never implied clear, and no flagged deal is left out. |

The mechanical comparison is in
[`portable-skill-diff-report.md`](portable-skill-diff-report.md). The synchronization policy is
in [`agent-plugin/CONVERSION_RECIPE.md`](../agent-plugin/CONVERSION_RECIPE.md).

## 2. Package layout

```text
agent-plugin/
├── plugin.json
├── mcp.json
├── skills/                         # all 34 upstream skills + twelve approved deviations
├── com.salesforce.quick/           # unverified Quick-specific extension placeholder
├── SETUP.md
├── CONVERSION_RECIPE.md            # upstream sync and deviation policy
└── evals/                           # static, live-read, MCP, browser, and judge harnesses
```

`plugin.json` contains the closed Agent Plugins manifest. `mcp.json` declares Headless 360 and
Slack as HTTPS Streamable HTTP servers and contains no credentials. OAuth client IDs, tokens,
and connector authorization are client-managed.

## 3. Output and MCP Apps behavior

The upstream delivery contract remains intact:

1. Gather and assemble grounded data.
2. When `display_widget` exists and the host can mount the App, hydrate and render the embedded
   widget once.
3. If the tool is unavailable, errors, or cannot render, use the source text fallback.

Headless 360 advertises `ui://widget/salesforce-widget-renderer` with
`text/html;profile=mcp-app`. Its tool response mirrors the submitted widget in
`structuredContent.widgetDefinition` and `_meta["salesforce/uiMetadata"]`.

Renderer compatibility is host-dependent. The Salesforce renderer stalls at `Loading…` in the
opaque-origin path used by the official basic host and MCP Inspector. It renders in a sandbox
that preserves a non-opaque renderer origin. The positive test uses separate loopback origins
and `sandbox="allow-scripts allow-same-origin"`, which preserves host/renderer origin isolation.
Amazon Quick has rendered selected synthetic workflows successfully; package-wide sandbox and MCP
Apps behavior remains unverified.

## 4. Salesforce calls and safety

The normal workflows use documented `dispatch_readonly` GET calls. No current skill contains an
executable general `dispatch` call. The static validator does not use a text-token denylist;
actual authorization belongs in Salesforce and the client.

Safety is validated in layers:

| Layer | Control |
|---|---|
| Salesforce/client | Least-privilege OAuth, permission sets, record access, and tool policy |
| Skill instructions | Existing upstream read, grounding, citation, and consent rules |
| Static validator | Packaging, frontmatter, query decoding/bracket balance, and declared posture |
| Local MCP adapter | Rejects POST, non-query endpoints, GraphQL mutations, and non-SELECT SOQL before Salesforce |
| Browser action host | Records and acknowledges actions without sending messages, opening links, or writing Salesforce |

There are 31 workflow `eval.yaml` contracts: 28 read-only and three draft-only
(`draft-outreach`, `call-follow-up`, and `inbox-sweep`). The utility skills `configure`,
`update`, and `using-display-widget` are part of the 34-skill mirror but do not have workflow
eval specs. Draft and Slack output requires human review before delivery.

## 5. Verification status

| Check | Current result | What it proves |
|---|---|---|
| Skill inventory/diff | 34 shared; 22 exact matches; 12 approved differences | Mirror fidelity |
| Static validator | PASS | Packaging, frontmatter, query syntax, posture checks |
| Read fixtures | PASS on `genwatt-demo` | Fixture GraphQL reaches a synthetic org and returns valid data |
| Exact skill calls | 157/157; six guards pass | Every documented read, including Configure's allowlisted UI API layout GET, executes through the read-only MCP adapter |
| Active widget parity | 25 exact contracts + 1 approved calendar subtitle correction | Active renderer JSON remains upstream-identical while the approved active contract delta is checked |
| Hosted widget contracts | 26/26 | Headless 360 returns the submitted active widgets and fallback content |
| Ravelin browser suite | 26/26; 130/130 semantic checks | Meaningful widgets visibly render in a compatible isolated host |
| Capture-only actions | 59/59: 39 messages, 20 links | Every declared action crosses the MCP Apps boundary with exact payloads |
| Quick host-run behavior | Partial: synthetic `calendar-events`, `customer-health`, `daily-briefing`, and `deal-advance-gap` widgets rendered; `customer-voice` text output followed its local rules | Selected routing/read/render paths work, including the health no-rewrite safeguard, case-total correction, customer-voice zero-quote rules, daily-briefing meeting-account correction, and deal-advance-gap lookup and stage-order corrections; remaining skills require host runs |

The Ravelin browser suite uses a canonical synthetic account, contacts, opportunities, team,
and portfolio. Every widget case supplies every active token explicitly, asserts five independent
business facts, captures a screenshot, and rejects generated placeholder values.

The daily-briefing LLM-judge calibration is historical and has not been re-baselined as part of
the current upstream-mirror reset. Do not treat it as current release evidence until rerun.

## 6. Host status

| Host/surface | Status |
|---|---|
| Direct hosted Headless 360 protocol | Tested with OAuth PKCE; raw widget JSON and renderer HTML captured |
| Compatible cross-origin browser shim | 26/26 widgets and 59/59 capture-only actions pass |
| Official MCP Apps basic host | Retrieves App/result; Salesforce renderer stalls in opaque sandbox |
| MCP Inspector App Review | Retrieves App/result; same opaque-sandbox stall |
| Kiro chat rendering | Raw tool path observed; visible App mounting not established |
| Amazon Quick | `calendar-events` and `customer-health` validated with synthetic Salesforce data and rendered widgets; other skills and action execution remain unverified |
| Claude/Cowork source plugin | Preserved upstream; not revalidated by this package's host suite |

## 7. Remaining work

1. Install the package in Quick and confirm discovery of all 34 skills.
2. Determine how Quick maps the Headless 360 read tool and whether it mounts MCP Apps.
3. Run trigger/routing, output-rubric, and email draft/never-send contracts in the actual host.
4. Resolve or report the Salesforce renderer's opaque-origin sandbox incompatibility.
5. Re-baseline LLM-judge calibration against the current upstream mirror if it remains a release
   gate.

## 8. References

- [Agent Plugins v1.0.0](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md)
- [Agent Skills specification](https://agentskills.io/specification)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Salesforce hosted MCP client connections](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/client-connection-overview.html)
- [Salesforce hosted MCP security](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/security-best-practices.html)
- [`agent-plugin/SETUP.md`](../agent-plugin/SETUP.md)
- [`agent-plugin/evals/README.md`](../agent-plugin/evals/README.md)
- [`agent-plugin/evals/mcp_apps/README.md`](../agent-plugin/evals/mcp_apps/README.md)

Content derived from external documentation was rephrased for compliance with licensing
restrictions.
