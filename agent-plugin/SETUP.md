# Setup: Salesforce, MCP Apps, and optional connectors

The active package mirrors all 34 upstream skills. Salesforce reads use Headless 360
`dispatch_readonly`; 26 skills also use `display_widget` for widget-first output and retain a
text fallback.

## Declared MCP servers

`mcp.json` declares the same hosted endpoints as the source plugin:

| Server | URL | Purpose |
|---|---|---|
| `salesforce-h360` | `https://api.salesforce.com/platform/mcp/v1/platform/headless-360` | Salesforce reads and MCP Apps widgets |
| `slack` | `https://mcp.slack.com/mcp` | Optional internal context and draft Slack content |

Whether a client loads bundled `mcp.json` is host-specific. Amazon Quick connector mapping,
plugin loading, and MCP Apps rendering have not been verified in this repository. Do not treat
the package declaration as proof of Quick support.

## Headless 360 tools

| Tool | Role in the active skills |
|---|---|
| `dispatch_readonly` | Required for the documented Salesforce GraphQL, SOQL, and UI API reads. |
| `display_widget` | Required for widget-first output on a compatible MCP Apps host. |
| `discover`, `describe` | Not used by the normal skill workflows; the upstream skill rules tell the agent not to call them. |
| `dispatch` | General REST tool that can mutate data; no current skill contains an executable `dispatch` call. |

The static validator does not maintain a substring denylist. Real authorization belongs at the
Salesforce permission/tool layer and in the client. For a read-only deployment, use least
privilege and disable tools the deployment does not need. Do **not** disable `display_widget` if
you expect the upstream widget-first behavior. A client-side read-only policy might disable
`dispatch` while allowing `dispatch_readonly` and `display_widget`; exact controls depend on the
client and org policy.

## Skill calls and approved differences

GraphQL reads encode the document inside `queryInput`:

```text
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })
```

SOQL reads use `/services/data/v63.0/query` and `queryParams: { "q": "SELECT ..." }`.
Per-call API versions remain as upstream. Only three active skill differences are allowed:

- [`lead-triage` #9](https://github.com/salesforce/salesforce-skills/issues/9): User and Group
  owner fragments.
- [`forecast-narrative` #15](https://github.com/salesforce/salesforce-skills/issues/15): UTC
  DateTime boundary for field history.
- [`weekly-wrap` #16](https://github.com/salesforce/salesforce-skills/issues/16): two
  dispatches instead of one 12-root request.

A host with a differently named Salesforce read connector would need to map the same URL/query
contract to that connector. That mapping remains unverified for Quick.

## MCP Apps renderer compatibility

Headless 360 advertises `ui://widget/salesforce-widget-renderer` and returns each submitted
widget in both `structuredContent.widgetDefinition` and `_meta["salesforce/uiMetadata"]`.
The live hosted contract suite verifies all 26 active widget definitions.

Host sandbox behavior matters:

- The official basic host and MCP Inspector retrieve the App and populated result, but their
  opaque-origin path leaves this Salesforce renderer at `Loading…`.
- A separate-origin renderer sandbox with `allow-scripts allow-same-origin` completes the
  handshake and renders. The host and renderer remain isolated because they use different
  origins.
- The Ravelin browser suite validates 26/26 widgets and capture-only actions in that compatible
  configuration.

If a client cannot mount the renderer, the skill must use its upstream text fallback. See
[`evals/mcp_apps/README.md`](evals/mcp_apps/README.md) for protocol, hosted, browser, and safety
details.

## Salesforce OAuth setup

Follow the source plugin's [setup guide](../salesforce-for-sales/SETUP.md):

1. Activate the Salesforce MCP Server.
2. Create a permission set for intended users.
3. Create an External Client App (ECA).
4. Add the `mcp_api` scope and require PKCE.
5. Connect the client and apply least-privilege tool/record permissions.

The package cannot contain a Consumer Key or secret. A client that does not support dynamic
registration must be configured separately with the ECA Consumer Key. For Kiro, define the
server in workspace or user MCP settings and set `oauth.clientId`. Use a public PKCE client and
register the exact `http://localhost:<port>/...` redirect URI sent by the client.

## Local read-only testing

`evals/local-mcp/salesforce-readonly-mcp` runs the skills' read calls through an existing `sf`
CLI login. It exposes Headless 360's `dispatch_readonly` signature, accepts only documented GET
GraphQL/SOQL reads plus Configure's exact v63.0 Opportunity Full/View UI API layout read, and
rejects mutations, non-SELECT SOQL, and every other REST route before contacting Salesforce.

Example Kiro workspace entry:

```json
{
  "mcpServers": {
    "salesforce-readonly": {
      "command": "/absolute/path/to/agent-plugin/evals/local-mcp/salesforce-readonly-mcp",
      "args": [],
      "env": { "SF_TARGET_ORG": "genwatt-demo" }
    }
  }
}
```

Always use an org with synthetic data. This local adapter does not implement `display_widget`;
use the hosted MCP Apps and browser suites for renderer validation.

## Slack, email, calendar, and documents

Slack is the only optional non-Salesforce server declared in `mcp.json`. Email, calendar, and
document tools must be configured separately when a host supports them. Draft workflows must
remain draft-only until a user approves the exact message and destination. A missing optional
connector should lead to the upstream fallback behavior, not fabricated evidence.
