# Symphony Setup

Symphony Forge uses **Codex** as the core execution runtime, with **OpenClaw + ACPX** as the orchestration option.

The old Symphony idea still maps conceptually to the system:
- Linear issue -> work item
- branch/worktree -> isolated environment
- coding agent -> Codex session
- PR -> delivery artifact

The concrete runtime can be either plain Codex or OpenClaw ACP orchestration.

---

## Prerequisites

- A project scaffolded from Symphony Forge
- A Linear workspace with API access
- A GitHub repo with Actions enabled
- Optional OpenClaw Gateway configured with:
  - `acp.backend = "acpx"`
  - `acp.defaultAgent = "codex"`
- Codex logged in with subscription auth

---

## Step 1: Configure Linear

Linear remains the source of truth.

Recommended states:
- `Backlog`
- `Planning`
- `Awaiting Approval`
- `In Progress`
- `Review`
- `PR Ready`
- `Done`
- `Blocked`

Branch naming should derive from Linear issue IDs:

```text
feat/ENG-123-short-description
```

---

## Step 2: Choose Runtime Mode

### Option A: Plain Codex

Use when you want the repo to run directly with Codex:
- `planner-high` creates the plan
- `docs-decomposer` records decomposition
- implementation runs locally
- testing and review use the project-scoped Codex subagents

### Option B: OpenClaw + ACP/ACPX

Use when you want long-running orchestration:
- OpenClaw `main` orchestrates planning, decomposition, review, and tracker sync
- ACP `codex` sessions implement feature tasks
- after verification, the parent Codex session spawns testing and review subagents
- the session label includes the Linear key

Example local ACP target:

```bash
acpx openclaw exec "Summarize the active implementation state."
```

For stable local use, set `~/.acpx/config.json` so `openclaw` points to your local gateway and default session.

---

## Step 3: Configure GitHub

GitHub is the execution mirror:
- branch
- draft PR
- PR comments for plan, verify, and review summaries

Use GitHub Actions for deterministic checks on push and PR.

---

## Step 4: Configure Docs and Factory State

Put the application inputs directly in the repo before planning:
- `docs/product/BRIEF.md`
- `docs/architecture/`
- `docs/decisions/`

Each repo keeps run state under `.factory/`:
- `run.json`
- `decomposition.json`
- `verify.json`
- `tests.json`
- `reviews/*.json`

Initialize a run with:

```bash
python3 .agents/scripts/intake.py --issue ENG-123 --title "Feature title"
```

---

## Step 5: Human Approval Points

The factory is not fully autonomous.

Required human approval points:
1. after planning and decomposition
2. before merge

Everything else can be handled by the factory loop.
