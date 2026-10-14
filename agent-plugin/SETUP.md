# Setup: connecting the skills to Salesforce and Slack

The skills read Salesforce through an MCP server. `mcp.json` declares the same two hosted
servers as the original Claude plugin (`salesforce-for-sales/.mcp.json`):

| Server | URL | Used for |
|---|---|---|
| `salesforce-h360` | `https://api.salesforce.com/platform/mcp/v1/platform/headless-360` | all Salesforce reads |
| `slack` | `https://mcp.slack.com/mcp` | internal context and Slack drafts |

Amazon Quick doesn't use `mcp.json`. It connects to Salesforce and Slack through connectors
set up in the Quick console, so everything below about `mcp.json` applies to clients that load
a plugin's bundled servers, such as Kiro.

## Keep Headless 360 read-only

The original plugin's `.mcp.json` described the server's five tools and marked three to block.
The Agent Plugins format has no `description` field, so that guidance lives here.

| Tool | What it does | Setting |
|---|---|---|
| `discover` | searches Salesforce's APIs for operations | **block** |
| `describe` | returns the full spec of an operation or object | **block** |
| `dispatch` | runs any REST call, including creates and updates | **block** |
| `dispatch_readonly` | runs read-only REST calls (SOQL, UI API, GraphQL) | allow |
| `display_widget` | renders a Claude/Cowork widget | block (the portable skills don't use it) |

The skills need only `dispatch_readonly`.

Enforce this in Salesforce, where the model can't get around it: restrict the tools on the
org's MCP server (step 5 of the original setup below). A client-side block is a second layer:

- **Kiro, server defined in workspace or user MCP settings:** `disabledTools` on the server
  entry, e.g. `"disabledTools": ["discover", "describe", "dispatch", "display_widget"]`.
- **Kiro, server bundled in this Power:** Kiro namespaces it (for example
  `power-salesforce-for-sales-salesforce-h360`). Kiro's docs don't say whether `disabledTools`
  or the MCP panel's per-tool Disable apply to a Power's servers. Check at first install.
- **The skills** also say never to use `discover` or `describe` and to stay read-only. That's
  an instruction, not a block.

## How the skills call Salesforce

The skills keep the original plugin's Headless 360 calls unchanged, for example:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })
```

GraphQL reads put the query in a JSON string under `queryInput`; SOQL reads use
`url: "/services/data/v63.0/query"` with `queryParams: { "q": "SELECT ..." }`. Each call keeps
its API version (some pin `v66.0` or `v63.0`).

On a host whose Salesforce connector has a different read tool (for example, Amazon Quick),
the model sends the same `url` and query through that tool. That mapping is untested.

## Salesforce admin setup

From the original plugin's [SETUP.md](../salesforce-for-sales/SETUP.md) and
[What Is Salesforce in Claude](https://help.salesforce.com/s/articleView?id=sales.what_is_salesforce_in_claude.htm&type=5):

1. Activate the Salesforce MCP Server in Setup.
2. Create a permission set for the users who should have access (recommended).
3. Create and configure the External Client App (ECA) for OAuth.
4. Connect the client to Salesforce MCP.
5. Set tool restrictions to keep it read-only (the table above).

**Sign-in in Kiro.** The original setup puts the ECA's Consumer Key in the MCP config. A
`streamable-http` entry in the Agent Plugins format allows only `type`, `url`, and `headers`,
so there's no place for it here. Salesforce's hosted MCP servers don't support dynamic client
registration: an admin registers an ECA and the client is configured with its Consumer Key
(see `docs/agent-plugin-spec.md`, section 7, for sources). So the bundled `salesforce-h360`
entry can't sign in by itself. Define the server in Kiro's workspace or user MCP settings
instead, with Kiro's `oauth.clientId` set to the Consumer Key.

Kiro supports only public clients (PKCE, no client secret, local redirect). Salesforce supports
that: in the ECA, keep PKCE required, deselect "Require secret for Web Server Flow", and add
the `mcp_api` scope. Register the callback as `http://localhost:<port>/...`; an HTTP callback
on `127.0.0.1` is reported to be rejected. Which exact redirect URI Kiro sends is untested,
so check it at first sign-in and register that.

Until the org is set up, the bundled `salesforce-h360` server fails to connect. Per the spec
that's a connection failure, not a broken plugin: the skills still load, but can't read
Salesforce. Disable that server in Kiro's MCP panel while testing with the local server below.

## Testing locally without Headless 360

`evals/local-mcp/salesforce-readonly-mcp` is a small, dependency-free MCP server that runs the
skills' reads through your `sf` CLI login. It offers one tool, `dispatch_readonly`, with the
same signature as Headless 360's, so the skills' calls run unchanged. It supports only GET on
the GraphQL and SOQL query endpoints, rejects GraphQL mutations and non-SELECT SOQL before
calling Salesforce, and never handles an access token. It's a test tool, not part of the
shipped plugin.

To use it in Kiro, add it to `.kiro/settings/mcp.json` in your workspace (use your own path and
org alias):

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

`SF_TARGET_ORG` picks the org; without it, `sf` uses its default target org. Use an org with
synthetic data. Kiro asks before each tool call unless you approve the tools.

## Slack and other connectors

Slack is the only non-Salesforce server declared. Email, calendar, and document connectors
aren't declared; connect them separately in the client if you want those sources. Without them
the skills use Salesforce data only, and the draft skills return email text instead of creating
a draft. Slack content stays a draft until the user approves the exact message and channel.
