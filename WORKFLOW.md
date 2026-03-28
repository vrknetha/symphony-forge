# WORKFLOW.md — Codex ACP Factory

## Source of Truth
- Linear owns task state and prioritization.
- GitHub mirrors execution state, branch, PR, and review evidence.
- OpenClaw `main` orchestrates. ACPX `codex` sessions implement.

## Branch Naming
- `feat/<LINEAR-KEY>-<slug>` for new work
- `fix/<LINEAR-KEY>-<slug>` for bug work

## Factory Phases
1. `planning`
2. `awaiting-approval`
3. `implementing`
4. `reviewing`
5. `pr-ready`
6. `done` or `blocked`

## Runtime Split
- Planning: `claude-opus-4-6` or `gpt-5.4` high reasoning
- Implementation: ACP/ACPX `codex`
- Review: Codex read-only subagents `quality-reviewer`, `performance-reviewer`, `security-reviewer`

## Required Artifacts
- Approved plan
- `.factory/run.json`
- `.factory/verify.json`
- `.factory/reviews/quality.json`
- `.factory/reviews/performance.json`
- `.factory/reviews/security.json`

## Deterministic Verification
Always use:
```bash
python3 .codex/scripts/verify.py
```

## Review Flow
After verification passes, the parent Codex session explicitly spawns:
- `quality-reviewer`
- `performance-reviewer`
- `security-reviewer`

The parent session waits for all three results, then records structured review artifacts with `record_review_from_json.py` or `record_review.py`.

Expected artifact fields:
- `aspect`
- `score`
- `summary`
- `blocking_findings`
- `non_blocking_findings`
- `residual_risks`
- `recommendation`
- `reviewed_scope`

## PR Ready Contract
A branch is PR-ready only when:
- deterministic verification passes
- all three review artifacts exist
- no review has blockers
- every review score is at least 8/10
- acceptance criteria have evidence
