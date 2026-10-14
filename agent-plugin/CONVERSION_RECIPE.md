# Skill Conversion Recipe

How to convert a `salesforce-for-sales` skill from the Claude Code / Cowork plugin format
into a portable **Agent Plugin** skill under `agent-plugin/skills/<name>/SKILL.md`.

Three skills are already converted as worked references — read them before starting:
`daily-briefing` (read-only, multi-connector), `call-prep` (branchy resolution),
`draft-outreach` (write path / draft-only). Follow their patterns exactly.

## Source and destination

- **Source:** `salesforce-for-sales/skills/<name>/SKILL.md`
- **Destination:** `agent-plugin/skills/<name>/SKILL.md` (create the directory). This folder
  ships with the skill, so it holds only `SKILL.md` plus any real `scripts/` or `references/`
  the skill uses.
- **Eval files:** `agent-plugin/evals/skills/<name>/eval.yaml` and
  `agent-plugin/evals/skills/<name>/reads/*.graphql`. Never put them in the skill folder; the
  validator blocks it. See `evals/README.md`.
- Do **not** modify the source. The Claude plugin stays intact.

## The 6 steps

### 1. Keep the frontmatter verbatim
Copy `name` and `description` exactly. `name` MUST equal the directory name (Agent Skills
spec). Do not add other frontmatter fields.

### 2. Keep the global-rules bootstrap, minus the widget rule
Copy the original `<!-- global-rules-bootstrap -->` block verbatim (it's identical in every
original skill), including its Headless 360 connectivity check and its rule to use only the
skill's `dispatch_readonly` calls. Remove only the `⛔ WIDGET OUTPUT ONLY` bullet (it's
Claude widget-specific).

Then add the **Portability note** blockquote just before `<!-- /global-rules-bootstrap -->`
(copy from a converted skill), adjusting the read-only vs. write wording to match the skill
(see step 5). It says calls use Headless 360 `dispatch_readonly`, and that a host with a
different Salesforce read tool (e.g. Amazon Quick) sends the same `url` and query through it.

### 3. Keep the Headless 360 calls verbatim
Salesforce calls stay exactly as the original writes them: `dispatch_readonly(method: "GET",
url: ..., queryParams: { "queryInput": "{\"query\":\"...\"}" })` for GraphQL and
`queryParams: { "q": "SELECT ..." }` for SOQL. Copy the call text from the original file;
don't retype or unescape it (retyping these nested escapes dropped braces in 11 queries
during the first conversion). Keep per-call API versions (some pin `v66.0` or `v63.0`).

- Writes (`dispatch(...)`) aren't used by any skill; if one appears, see step 5.
- Keep any documented error-recovery notes (e.g. "re-issue without the `Events` block").
- A call you add (not in the original) uses the same format. Build `queryInput` with
  `json.dumps(json.dumps({"query": q}, separators=(",", ":")))` and check it decodes back to
  the query.
- **Totals come from Salesforce, never from the model.** If the skill shows a count or dollar
  total for a list (e.g. "13 opps, $5.1M"), add an aggregate read with the **exact same**
  `scope` and `where` as the row read, issued in the same turn. The query (wrap it in a
  `dispatch_readonly` call as above):
  ```
  query { uiapi { aggregate { Opportunity(scope: MINE, where: { <same filter> }) { edges { node { aggregate { Amount { sum { value displayValue } } Id { count { value } } } } } } } } }
  ```
  Then add the rule: show totals only from the aggregate (`displayValue`), never add up or count
  rows yourself; say "showing [rows] of [count]" when the count exceeds the rows listed; if the
  aggregate fails, show rows without a total. Add a matching
  `evals/skills/<skill>/reads/<name>-total.graphql` fixture. Why: in testing, the model mis-added a 13-row list by $57,000, and row reads stop
  at `first: 50`, so a model sum can be both wrong and incomplete. Verified on v65.0 with
  `scope: MINE`. Math Salesforce can't do (scenario or weighted-forecast models) is the one
  case where a bundled `scripts/` helper is justified, with a fallback for hosts that can't
  run scripts.

### 4. Remove the widget; promote text to the primary output
- Delete the entire `display_widget` section: the `## N. Widget` heading, the variable
  contract JSON, and the renderer JSON template.
- Take the old `## N. Text — FALLBACK ONLY` block and make it the primary output section:
  rename to `## N. Output — <deliverable> (primary, portable)`, drop the "FALLBACK ONLY /
  DO NOT USE IF display_widget SUCCEEDED" caveat, and keep the Markdown template.
- If the skill flagged data the widget showed but the text didn't (e.g. a past-due
  section), fold it into the text output so nothing is lost.
- Add a final `## N. Rich visualization (host-specific — optional)` section (copy from a
  converted skill) pointing to `com.salesforce.quick/ui`.

### 5. Preserve the read/write consent posture — do not weaken it
Classify the skill first:
- **Read-only skill** (most of them: briefings, reviews, research, context, maps): state
  "Read-only: never writes to Salesforce" in the intro and portability note.
- **Draft/guided-write skill** (`draft-outreach`, `call-follow-up`, `inbox-sweep`, and any
  that create email/records): keep the **draft-then-human-sends** contract explicit and
  loud. Never auto-send. If the skill wrote to Salesforce via `dispatch`, keep it
  approval-gated and clearly labeled; if the connector is read-only, provide manual
  guidance instead (as the originals do). The safety contract is non-negotiable and must
  survive the port.
- **Draft/send skills also get the `email_eval` block in their `eval.yaml`.** Copy the
  `email_eval:` block from `evals/skills/draft-outreach/eval.yaml` — it's the reusable template.
  It's a HOST-RUN tier (executed in Quick, where the email connector lives), gated on
  connector availability (SKIP when absent), and asserts draft-created / not-delivered /
  no-autosend. A real send is off by default and only ever runs with an explicit operator
  opt-in to an allowlisted, non-CRM test recipient. Skills that need it: `call-follow-up`
  (drafts a customer email + internal Slack recap), `inbox-sweep` (batch draft replies).

### 6. Validate
Run the validation block below. Fix anything before moving on.

## Validation

```bash
cd agent-plugin
python3 evals/validate.py <name>                       # static checks (no org, no model)
python3 evals/run_reads.py --org <sandbox-alias> <name>  # read fixtures run on a live org
```

Pass criteria (enforced by `validate.py`): `name` matches the directory, `description`
present, ideally < 500 lines, no `display_widget` / `dispatch(` / `discover(` / `describe(`
tokens, every `dispatch_readonly` query decodes with balanced brackets, the consent posture
from `eval.yaml` holds, and no eval-only files (`eval.yaml`, `reads/`) inside the skill folder.

## Remaining skills (27)

Read-only conversions (straightforward — apply steps 1–4, mark read-only in step 5):
`account-context`, `account-tiering`, `calendar-events`, `close-plan`, `customer-health`,
`customer-voice`, `deal-advance-gap`, `deal-review`, `deal-signals`, `deal-slip-scenario`,
`expansion-whitespace`, `find-internal-answer`, `forecast-narrative`, `handle-objection`,
`lead-triage`, `pipeline-review`, `query-activity-history`, `renewal-radar`, `rep-context`,
`research-prospect`, `salesforce-hygiene-check`, `stakeholder-map`, `team-pipeline`,
`weekly-wrap`, `win-loss-review`.

Write/draft-path conversions (apply step 5 carefully):
`call-follow-up` (drafts email + internal summary), `inbox-sweep` (batch draft replies).
Also re-check `salesforce-hygiene-check` — if it proposes record edits, treat as guided
write (approval-gated), not read-only.

Special cases (already decided):
- `voice-profile` → keep as a portable skill (email-only workflow, produces a deliverable).
- `using-display-widget` → do **not** port to the portable core; its content becomes the
  basis for `com.salesforce.quick/ui` (host-extension rendering guidance).

## Notes

- **`$schema` in JSON files:** the `plugin.json` (and future `mcp.json`) `$schema` line may
  need to be added by hand in Supervised mode — the editing tools block writing a `$schema`
  key that points at a remote URL. In Autopilot this restriction does not apply. The spec
  requires the field; clients do not fetch it at load time.
- **`mcp.json`:** declares Salesforce Headless 360 and Slack as `streamable-http`, mirroring
  the original `.mcp.json`. Quick ignores it (it uses console-registered connectors); clients
  like Kiro load it. The original's server `description` (which Headless 360 tools to block)
  isn't allowed in the Agent Plugins format, so that guidance is in `SETUP.md`. A local
  `sf`-backed test server lives in `evals/local-mcp/`.
- **Batching:** preserve every "issue these in ONE turn" instruction — it's a real
  performance contract, not decoration.
