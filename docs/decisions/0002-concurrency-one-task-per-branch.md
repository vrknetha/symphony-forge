---
status: accepted
confirmed_by: "Ravi"
date: 2026-07-14
---

# Concurrency: one task per branch

## Context

`.factory/run.json` holds ONE active task, so a team of devs working
parallel stories needs a concurrency model. Options considered: one task
per branch with committed `.factory/` state, or git worktrees with
uncommitted state.

## Decision

One task per branch. intake names the branch (`feat/<key>-<slug>`), the
task's `.factory/` state is committed on that branch through the loop, and
`pr_ready.py` archives evidence to `.factory/history/<issue>/` before merge.
Parallel devs = parallel branches; the roadmap's status flips merge normally
and `.gstack` JSONL stores union-merge via the jsonl-append driver.

## Consequences

- Evidence is reviewable in the PR alongside the code it attests to.
- main only accumulates archived history, never in-flight task state.
- Two branches merged in sequence may conflict on `.factory/run.json`;
  resolution is trivial (the later task's state wins — both are archived).
- Worktrees remain possible on top (a worktree is just a branch checkout);
  the harness does not manage them.
