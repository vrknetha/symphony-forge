# Getting Started with Symphony Forge

Symphony Forge is a harness plus Codex/OpenClaw factory scaffold for building agent-ready software.

---

## Prerequisites

| Tool | Minimum version |
|------|-----------------|
| Node.js | 20.x |
| pnpm | 9.x |
| Docker Desktop | recent |
| Git | 2.x |
| OpenClaw | current |
| Codex login | subscription auth |

---

## Use as a GitHub Template

Create a new repo from `vrknetha/symphony-forge`, then clone it.

```bash
gh repo create my-org/my-app --template vrknetha/symphony-forge --private

git clone git@github.com:my-org/my-app.git
cd my-app
```

---

## Initialize a Feature Run

```bash
python3 .codex/scripts/intake.py --issue ENG-123 --title "Build billing dashboard"
```

That creates `.factory/run.json` and establishes the issue/branch contract.

---

## Plan First

Use a high-reasoning planner to create the approved plan artifact before implementation.

When approved, move the run forward:

```bash
python3 .codex/scripts/update_run.py --phase implementing --plan-status approved
```

---

## Implement via ACP Codex

Use OpenClaw + ACPX Codex for coding work. Keep the coordinator thin-context and use persistent ACP coding sessions for implementation.

---

## Verify Deterministically

```bash
python3 .codex/scripts/verify.py
```

This writes `.factory/verify.json`.

---

## Spawn Review Subagents

After verification passes, have the parent Codex session explicitly spawn:
- `quality-reviewer`
- `performance-reviewer`
- `security-reviewer`

These are project-scoped custom agents defined under `.codex/agents/`. They are read-only and framework-independent.

If the parent Codex session already has structured reviewer JSON, prefer:

```bash
python3 .codex/scripts/record_review_from_json.py --aspect quality --input /tmp/quality-review.json
python3 .codex/scripts/record_review_from_json.py --aspect performance --input /tmp/performance-review.json
python3 .codex/scripts/record_review_from_json.py --aspect security --input /tmp/security-review.json
```

For manual fallback, record the results with:

```bash
python3 .codex/scripts/record_review.py --aspect quality --score 9 --summary "Code quality acceptable" --recommendation approve --reviewed-scope src/api/orders.ts
python3 .codex/scripts/record_review.py --aspect performance --score 8 --summary "No major regressions" --recommendation approve-with-caveats --reviewed-scope src/api/orders.ts
python3 .codex/scripts/record_review.py --aspect security --score 9 --summary "Security posture acceptable" --recommendation approve --reviewed-scope src/api/orders.ts
```

---

## Mark PR Ready

```bash
python3 .codex/scripts/pr_ready.py
```

If artifacts are missing or review thresholds are not met, it exits non-zero.
