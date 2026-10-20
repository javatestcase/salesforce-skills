# Quick/Kiro Skill Adaptation SOP

## Overview

Use this SOP when a Salesforce sales skill behaves differently in Quick or Kiro than it does in
its upstream Claude/Cowork environment. Its purpose is to preserve correct upstream behavior
while allowing evidence-backed local adaptations for Quick/Kiro.

### Governing tenets

1. **Upstream changes require a universal defect.** An upstream issue or source change is
   appropriate only when the skill is demonstrably incorrect independent of host: for example, a
   malformed literal query, invalid API contract, incorrect data calculation, security violation,
   or behavior that fails in more than one conforming host.
2. **Host-specific behavior belongs in the Quick/Kiro adaptation.** If the upstream skill works
   correctly in its intended host and a Quick/Kiro runtime needs different execution guidance,
   fallback behavior, or result handling, adapt the local Quick/Kiro skill instead of asking
   upstream to change working behavior.
3. **Do not add redundant fallbacks.** A host's documented default behavior is sufficient unless
   evidence shows that the host silently skips a required step, fabricates completion, violates a
   consent boundary, or otherwise fails the skill's intended outcome.
4. **Preserve user-visible semantics and safety.** A local adaptation may change execution
   mechanics for the host, but it must not invent facts, broaden data access, send instead of
   draft, silently substitute channels, weaken consent, or claim completion without evidence.

## Parameters

- **skill_name** (required): Kebab-case skill directory name, such as `account-context`.
- **host_evidence** (required): Reproducible Quick/Kiro trace, exact error, capability statement,
  or synthetic-host result that distinguishes host behavior from source behavior.
- **proposed_change** (required): Concise description of the local behavior to add, remove, or
  clarify.
- **target_host** (optional, default: `Quick/Kiro`): The host or host family the adaptation
  targets.
- **upstream_behavior** (optional): Relevant source behavior, issue, or source-file section used
  for comparison.

**Constraints for parameter acquisition:**
- If all required parameters are already provided, You MUST proceed to the Steps.
- If any required parameters are missing, You MUST ask for them before proceeding.
- When asking for parameters, You MUST request all parameters in a single prompt.
- When asking for parameters, You MUST use the exact parameter names as defined.

## Steps

### 1. Classify the observed behavior

Compare the unmodified upstream skill with the Quick/Kiro trace and identify the first point at
which they differ.

**Constraints:**
- You MUST inspect the literal source query, instruction, or fallback before attributing failure
  to upstream behavior.
- You MUST classify the finding as one of: `universal defect`, `host-specific adaptation`,
  `redundant proposal`, or `insufficient evidence`.
- You MUST NOT, as a safety and portability requirement, treat a host's reconstructed query, repair loop, tool narration, or unsupported
  capability as an upstream defect because the source may work when followed as written.
- You MUST use a synthetic or non-production environment for live validation because production
  records and credentials are not required to establish execution behavior.

### 2. Decide the change target

Choose upstream only for a proven universal defect; otherwise choose the local Quick/Kiro skill
layer or make no change.

**Constraints:**
- You MUST propose an upstream issue only when the source behavior is demonstrably incorrect or
  unsafe across hosts, with an externally understandable reproduction and narrow fix.
- You MUST NOT, as a safety and portability requirement, propose upstream wording solely to describe a Quick/Kiro limitation, tool name,
  temporary-file path, shell behavior, or host-default recovery because that would couple a
  portable skill to one runtime.
- You MUST choose `redundant proposal` when Quick/Kiro already provides an honest, safe fallback
  that preserves the skill outcome without extra skill text.
- You MUST choose `insufficient evidence` when no emitted request, error, or reproducible
  synthetic trace distinguishes source behavior from host behavior.

### 3. Design a local Quick/Kiro adaptation

When the evidence supports a host-specific change, adapt the local skill while retaining the
upstream skill as the reference behavior.

**Constraints:**
- You MUST preserve Agent Skills-compatible `SKILL.md` structure: valid YAML frontmatter with
  `name` and `description`, followed by portable Markdown instructions.
- You MUST express host behavior in terms of capabilities and outcomes, not unverified tool names
  or implementation details. For example, say to rebuild a canonical query from its template;
  do not require a particular shell, temporary-file path, or result-reader tool.
- You MUST keep execution-only tests, fixtures, and host adapters under `agent-plugin/evals/`;
  they MUST NOT ship inside a skill directory because a host can load every file in that directory
  as part of the distributable skill.
- You MUST keep the local adaptation narrowly scoped to the documented host difference and retain
  the upstream data, consent, and output semantics unless the evidence requires a change.
- You MUST update `agent-plugin/CONVERSION_RECIPE.md` and
  `docs/portable-skill-diff-report.md` in the same change when the first new Quick/Kiro
  divergence is implemented, because the current mirror policy allows only the three existing
  upstream-backed differences.
- You MUST NOT, as a safety and portability requirement, change the upstream source or create an external issue as part of a local
  Quick/Kiro adaptation unless Step 2 classified a universal defect, because that would impose a
  single host's workaround on clients where the source already works.

### 4. Validate the adaptation at the correct layer

Prove both the local mechanical change and the host behavior it addresses.

**Constraints:**
- You MUST add a deterministic offline test for template expansion, query shape, placeholder
  handling, or other mechanically verifiable behavior when applicable.
- You MUST run the relevant static validator, source-to-active diff/parity checks, and targeted
  tests before presenting the change.
- You MUST run a host-level test against synthetic data when the adaptation concerns runtime
  execution, tool routing, rendering, connector capabilities, or fallback behavior.
- You MUST document what the test proves and what remains unverified; a successful tool response
  alone does not prove rendered output, safe fallback behavior, or correct host routing.
- You MUST NOT, as a safety and portability requirement, use a production account, live customer data, or an outbound message to test a
  local adaptation because a synthetic test can establish the same behavior safely.

### 5. Record the decision and reassess upstream scope

Record the evidence, divergence rationale, validation results, and any remaining host limitation.

**Constraints:**
- You MUST state whether the result is an upstream issue, a local Quick/Kiro divergence, no
  change, or insufficient evidence.
- You MUST keep local issue records safe to share externally: use generic synthetic terminology
  and omit organization-specific identifiers.
- You SHOULD revisit an upstream change only if later evidence shows the same behavior is broken
  across intended hosts or violates a protocol/API contract independently of Quick/Kiro.
- You MUST NOT, as a safety and portability requirement, broaden a local divergence into a generic source rewrite without new evidence,
  because that would erase working upstream behavior for other clients.

## Examples

### Example 1: Canonical query works; Quick reconstructs it incorrectly

**Input:**
- `skill_name`: `account-context`
- `host_evidence`: Quick repairs braces and moves an aggregate block, but the exact source template
  succeeds when only documented placeholders are substituted.
- `proposed_change`: Add a local template-integrity instruction and offline substitution test.

**Expected behavior:**
Classify this as a `host-specific adaptation`. Do not file an upstream query-bug issue. Keep the
source query as the reference and adapt the Quick/Kiro skill only if the local host test proves
that the added instruction prevents the reconstruction failure.

### Example 2: Literal source query fails independently

**Input:**
- `skill_name`: `forecast-narrative`
- `host_evidence`: A documented date-only placeholder is used against a DateTime field and fails
  through the direct API and multiple conforming clients.
- `proposed_change`: Correct the DateTime predicate.

**Expected behavior:**
Classify this as a `universal defect`. Create an externally reproducible upstream issue with the
smallest query and error evidence, then apply only the approved local deviation.

### Example 3: Host default already handles a missing connector safely

**Input:**
- `skill_name`: `draft-outreach`
- `host_evidence`: Quick pauses when no email connector exists, does not send or fabricate a
  result, and offers connection or copyable-text recovery.
- `proposed_change`: Add a duplicate text fallback to the skill.

**Expected behavior:**
Classify this as a `redundant proposal`. Do not alter upstream or local skill behavior unless a
host trace shows that the default recovery violates the workflow's consent or outcome contract.

## Troubleshooting

### No host trace is available

Classify the work as `insufficient evidence`. Add an offline structural test if possible, but do
not file an upstream issue or create a local behavioral divergence based on speculation.

### The source and active skill differ unexpectedly

Stop and inspect `agent-plugin/CONVERSION_RECIPE.md` and
`docs/portable-skill-diff-report.md`. Reconcile the divergence rationale before adding another
local change.

### A proposed local fallback changes consent or delivery

Do not implement it automatically. For example, an email draft workflow must not switch to send,
and an email workflow must not silently switch to Slack. Require explicit user approval or a
source-defined channel substitution rule.
