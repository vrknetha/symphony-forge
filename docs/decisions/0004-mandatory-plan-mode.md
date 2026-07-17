---
status: accepted
confirmed_by: "Ravi"
date: 2026-07-15
---

# Planning is mandatory and hook-enforced before implementation

## Context

The plan ARTIFACT was gated (no implementation phase without an approved,
saved plan) but the process was not: a dev in normal mode could edit product
code while the task sat unplanned, discovering the gate only at record time.
The original gating model deliberately avoided keystroke-level blocks; the
platform owner overrode that for this one case.

## Decision

While an active, signed-off task has plan_status != approved, the PreToolUse
hook DENIES product-code edits (Edit/Write/MultiEdit/NotebookEdit outside
plans/docs/harness paths) and writing Codex delegation, instructing the
dev to switch Claude Code to PLAN MODE and plan per planner.md (or use the
Codex planner-high agent). Read-only exploration and planning-phase writes
stay open.

## Consequences

- No unplanned implementation can start, even accidentally; the hook
  message routes to plan mode rather than just refusing.
- This is the single sanctioned keystroke-level gate; every other gate
  remains at artifact transitions.
- Devs editing docs/decisions/plans during planning are unaffected;
  hotfix-style work still requires an intake + plan (fast plans are fine,
  skipped plans are not).
- Known boundary, accepted: arbitrary Bash mutations (sed -i, tee,
  redirects) are NOT classified by the lock — only the edit tools and Codex
  delegation are. Bash-level writes are backstopped by the artifact gates
  (unplanned work cannot pass verify/review/pr_ready), the same trust model
  as before this decision.
