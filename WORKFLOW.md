# WORKFLOW.md — Symphony-Style Codex Factory

## Source of Truth
- The repo owns workflow policy, prompts, run artifacts, plans, and decisions —
  it is the canonical state.
- An external tracker (Linear, GitHub Issues, Jira) is OPTIONAL: when one is
  used, decomposition and task state are mirrored into it; when none is used,
  `.factory/decomposition.json` and `plans/` are the task graph.
- GitHub mirrors branch, PR, checks, and review evidence.
- Product intent lives in `docs/product/BRIEF.md`.
- Architecture and decision docs live in the repo under `docs/architecture/` and `docs/decisions/`.
- `docs/decisions/` overrides ambiguous or conflicting architecture guidance.

## Runtime Modes
Claude Code coordinates; Codex executes (local sessions and subagents).
External orchestrators (e.g. OpenClaw ACP) are a future/optional mode — any
orchestration must produce the same `.factory` artifacts.

## Factory Phases
0a. `discovery` — lightweight problem, stakeholder, and constraint discovery; no `.factory` ceremony required.
0b. `prototype` — lightweight proof work before committing to the factory loop; no `.factory` ceremony required.
1. `planning`
2. `decomposing`
3. `awaiting-approval`
4. `implementing`
5. `testing`
6. `reviewing`
7. `functional-check`
8. `pr-ready`
9. `done` or `blocked`

The sign-off gate sits between `prototype` and `planning`. Record accepted client sign-off with `python3 .agents/scripts/record_signoff.py`, which sets `client_signoff` in `.factory/run.json`. `update_run.py` and `pre_tool_use.py` refuse phases at `planning` or later until that field is true.

## Context Inbox & Doc Upkeep

Unstructured context (client emails, transcripts, notes) goes in
`docs/context/` — dumping is free, tracking is mandatory. `forge.py context
scan` registers files in `docs/context/ledger.json` (CI enforces freshness);
an agent following `.agents/prompts/harvester.md` turns pending files into
proposed decision records and BRIEF/architecture edits, then marks them
harvested with their outputs. Check `context list --pending` before planning:
plans must not be written over unharvested context. Broader doc freshness
follows `harness/nestjs-react/conventions/doc-gardening.md` (gardening agent —
convention today, not yet automated).

## Evolution Loop

Dev corrections are the harness's training data. At retro cadence, an agent
following `.agents/prompts/skill-miner.md` mines recurring patterns (3+
occurrences: fix-after-review commits, repeated blockers, superseded
decisions) into PROPOSALS under `.agents/skills/proposed/` — skills, memory
lines, or constitution changes, each with cited evidence. Humans promote or
reject; nothing self-activates. The daily `gardener` workflow opens a
GitHub issue whenever unharvested context or unreviewed proposals exist, and
the SessionStart hook surfaces the same counts at the start of every agent
session. The `/forge` Claude skill routes all of this.

## Gating Model

Gates are deterministic and run at phase transitions (`update_run.py`, `record_*` scripts, `pr_ready.py`) and on Bash commands (`pre_tool_use.py`) — never on prompt keywords or turn ends. Editing files before plan approval is deliberately not hard-blocked: unapproved work cannot pass verify, testing, review, or `pr_ready.py`, which is where the contract is enforced. This replaces the earlier prompt-keyword and stop-hook guards, which had false positives in both directions and never actually covered non-Bash edits.

## Task Graph Rules
- The planner owns decomposition.
- Decomposition is capability-driven; the recorded artifact is canonical
  (mirror to a tracker if the project uses one).
- Each leaf task must have write scope, dependencies, acceptance criteria, verify commands, and reviewer focus.
- One task should fit one implementation session and one review package.

## Task Planning
Per-task planning runs in Claude Code plan mode by default (exploration
delegated to Codex read-only); devs may instead use the `planner-high` Codex
agent — the contract is identical either way. The plan follows
`.agents/prompts/planner.md`, including the mandatory **Decisions** section: every choice not derivable from BRIEF,
architecture, or existing records becomes a `docs/decisions/` record
(`forge.py decision new`) before decomposition is recorded. Approval means the
plan is in-repo — `forge.py plan save --from <plan-file>` writes
`plans/active/<issue>-<slug>.md`; `update_run.py` refuses
`plan_status approved` without it.

During implementation, any call the plan does not cover is recorded the moment
it is made — `forge.py plan assume "<one sentence>"` appends it, dated, under
`## Implementation Assumptions` on the active plan. The dev reviews the
section before merge and promotes durable assumptions to `docs/decisions/`;
`pr_ready.py` archives it with the plan. An assumption that would change
scope or acceptance criteria is a report back to the dev, not an assumption.

## Artifacts
Required run artifacts:
- `.factory/run.json`
- `plans/active/<issue>-<slug>.md` (the approved plan)
- `.factory/decomposition.json`
- `.factory/verify.json`
- `.factory/tests.json`
- `.factory/reviews/quality.json`
- `.factory/reviews/performance.json`
- `.factory/reviews/security.json`

On PR-ready, `pr_ready.py` archives the run artifacts to
`.factory/history/<issue>/` and moves the plan to `plans/completed/` — the
durable record of what was decided and what was built.

## Execution Order
1. ensure architecture and decision docs are present in-repo
2. complete discovery and prototype
3. record client sign-off
4. create an approved plan
5. record decomposition
6. implement one leaf task
7. run `automated-tester`
8. run `python3 .agents/scripts/verify.py`
9. spawn review subagents
10. run `functional-checker`
11. run `python3 .agents/scripts/pr_ready.py`

## PR Ready Contract
A branch is PR-ready only when:
- plan status is `approved`
- decomposition status is `recorded`
- deterministic verification passes
- automated and functional test artifacts exist with no blockers
- all three review artifacts exist with score >= 8 and no blockers
- acceptance criteria have direct evidence
