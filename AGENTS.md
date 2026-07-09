# AGENTS.md — Symphony Forge

## What This Repo Is

Symphony Forge is a dual-runtime software-factory template for turning in-repo architecture and decision docs into shipped applications.

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
4. `harness.yaml`
5. `constitution/README.md`
6. `docs/product/BRIEF.md`
7. `docs/architecture/`
8. `docs/decisions/`
9. the active plan and decomposition artifacts under `.factory/`

## Runtime Modes

Claude Code coordinates discovery, planning, decisions, and orchestration through `codex-plugin-cc`. During planning, codebase exploration is delegated to Codex read-only runs.

Codex executes exploration, implementation, testing, and review. The same `.factory` artifacts are required whether the repo runs in plain Codex or OpenClaw + ACP/ACPX mode.

## Phase Contract

0a. run lightweight discovery without `.factory` ceremony
0b. build a lightweight prototype without `.factory` ceremony
1. record client sign-off before planning
2. create or update the plan
3. generate decomposition
4. wait for approval
5. implement one bounded task
6. run automated testing
7. run deterministic verify
8. run review subagents
9. run functional checks
10. mark PR ready

Phases at `planning` or later are refused until `client_signoff` is true in `.factory/run.json`.
Implementation never starts before plan approval and recorded decomposition.

## Prompt and Agent Use

Prompt files under `.agents/prompts/` are phase contracts. They are invoked explicitly by the parent session; hooks only load context and enforce gates.

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
python3 .agents/scripts/intake.py --issue ENG-123 --title "Feature title"
python3 .agents/scripts/record_decomposition_from_json.py --input /tmp/decomposition.json
python3 .agents/scripts/update_run.py --phase awaiting-approval --plan-status awaiting-approval
python3 .agents/scripts/verify.py
python3 .agents/scripts/record_test_from_json.py --kind automated --input /tmp/automated.json
python3 .agents/scripts/record_review_from_json.py --aspect quality --input /tmp/quality.json
python3 .agents/scripts/pr_ready.py
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
