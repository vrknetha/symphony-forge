# AGENTS.md — Symphony Forge

## What This Is

Plan-driven engineering platform. High-reasoning planners define the work. ACP Codex workers implement it. Codex review subagents score it. Humans approve the plan and merge the PR.

## Runtime Split

- **Coordinator:** OpenClaw `main`
- **Planning:** `claude-opus-4-6` or `gpt-5.4` high reasoning
- **Implementation:** ACP/ACPX `codex`
- **Review:** Codex custom subagents `quality-reviewer`, `performance-reviewer`, `security-reviewer`

Keep the coordinator thin-context. Push coding work into ACP Codex sessions. Push review into isolated read-only subagents.

## Workspace

```text
.codex/                         -> Codex config, hooks, agents, prompts, deterministic scripts
.factory/                       -> Machine-readable run state
harness/nestjs-react/           -> Scaffold prompt + architecture conventions
plans/                          -> Active, completed, debt plans
projects/                       -> Project BRIEF.md files
WORKFLOW.md                     -> Issue/branch/PR/session contract
```

## Mandatory Read Order

1. `WORKFLOW.md`
2. `projects/<name>/BRIEF.md` (if present)
3. `plans/active/<name>.md` (if present)
4. Relevant convention files in `harness/nestjs-react/conventions/`

## The One Rule That Gates Everything

**Implementation does not start until the plan is approved.**

A task is not PR-ready until all of these exist:
- approved plan
- `.factory/run.json`
- `.factory/verify.json`
- three review artifacts under `.factory/reviews/`

## Deterministic Commands

Use these, not ad hoc variants:

```bash
python3 .codex/scripts/intake.py --issue ENG-123 --title "Feature title"
python3 .codex/scripts/update_run.py --phase awaiting-approval --plan-status awaiting-approval
python3 .codex/scripts/verify.py
python3 .codex/scripts/record_review.py --aspect quality --score 9 --summary "..."
python3 .codex/scripts/record_review_from_json.py --aspect quality --input /tmp/quality-review.json
python3 .codex/scripts/pr_ready.py
```

## Review Policy

Every implementation run gets three independent read-only review outputs:
- `quality-reviewer`
- `performance-reviewer`
- `security-reviewer`

Each reviewer must return:
- `score`
- `blocking_findings`
- `non_blocking_findings`
- `residual_risks`
- `recommendation`
- `reviewed_scope`

Scores must be >= 8/10 and blockers must be empty before PR-ready.

## ACP and Subagent Policy

Use ACP/ACPX Codex sessions for coding. Do not keep large implementation state in the coordinator session.

After deterministic verification passes, the parent Codex session must explicitly spawn the three review subagents, wait for all of them, and record their outputs into `.factory/reviews/`.

Recommended mapping:
- one Linear issue -> one branch
- one branch -> one persistent ACP Codex session label
- one PR -> one review package

## What Not To Do

- Do not implement before plan approval.
- Do not bypass `python3 .codex/scripts/verify.py` with direct test/lint/typecheck commands.
- Do not merge planning, implementation, and review into one vague session.
- Do not perform review inline when the custom review subagents can be spawned.
- Do not open a PR without review scores and deterministic verify results.
