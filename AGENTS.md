# AGENTS.md — Symphony Forge

## What This Repo Is

Symphony Forge is a software-factory template for turning in-repo architecture and decision docs into shipped applications.

It provides:
- planner-owned decomposition
- bounded implementation tasks
- deterministic verification
- testing and review subagents
- PR-ready proof artifacts

`AGENTS.md` stays short on purpose. Use it as a map.

## Mandatory Read Order

1. `WORKFLOW.md`
2. `docs/FACTORY.md`
3. `docs/QUALITY.md`
4. `docs/product/BRIEF.md`
5. `docs/architecture/`
6. `docs/decisions/`
7. the active plan and decomposition artifacts under `.factory/`

## Runtime Modes

Two modes are supported:
- **Plain Codex** — local Codex sessions and subagents
- **OpenClaw + ACP/ACPX** — orchestration and long-running issue execution

The repo must work in both modes. ACP is useful for orchestration, not required for normal use.

## Phase Contract

1. place architecture and decision docs in-repo
2. create or update the plan
3. generate decomposition
4. wait for approval
5. implement one bounded task
6. run automated testing
7. run deterministic verify
8. run review subagents
9. run functional checks
10. mark PR ready

Implementation never starts before plan approval and recorded decomposition.

## Prompt and Agent Use

Prompt files under `.codex/prompts/` are phase contracts. They are invoked explicitly by the parent Codex session; hooks only load context and enforce gates.

Default specialist set:
- `planner-high`
- `docs-decomposer`
- `automated-tester`
- `functional-checker`
- `quality-reviewer`
- `performance-reviewer`
- `security-reviewer`

## Reasoning Defaults

- planning / decomposition / architecture reconciliation: `high`
- implementation default: `medium`
- implementation escalation cases: `high`
- review and testing agents: explicit per-agent overrides

Do not default the entire repo to `high` reasoning for every task.

## Deterministic Commands

```bash
python3 .codex/scripts/intake.py --issue ENG-123 --title "Feature title"
python3 .codex/scripts/record_decomposition_from_json.py --input /tmp/decomposition.json
python3 .codex/scripts/update_run.py --phase awaiting-approval --plan-status awaiting-approval
python3 .codex/scripts/verify.py
python3 .codex/scripts/validate_artifacts.py
python3 .codex/scripts/validate_work.py
python3 .codex/scripts/stage_orchestrator.py
python3 .codex/scripts/record_test_from_json.py --kind automated --input /tmp/automated.json
python3 .codex/scripts/record_review_from_json.py --aspect quality --input /tmp/quality.json
python3 .codex/scripts/pr_ready.py
```

## Hard Gates

A task is not PR-ready until all of these exist:
- approved plan
- `.factory/run.json`
- `.factory/decomposition.json`
- `.factory/verify.json`
- `.factory/tests.json`
- `.factory/reviews/quality.json`
- `.factory/reviews/performance.json`
- `.factory/reviews/security.json`

## Non-Negotiables

- Keep tasks bounded and capability-driven.
- Do not decompose by document file or arbitrary file count.
- Do not bypass `verify.py` with ad hoc validation commands.
- Do not do review inline when review subagents can be spawned.
- Keep the template repo independent of any client-specific source repo.
- Do not keep long policy blocks in `AGENTS.md`; move them into docs.
