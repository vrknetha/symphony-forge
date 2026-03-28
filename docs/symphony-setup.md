# Symphony Setup

Symphony Forge now uses **OpenClaw + ACPX + Codex** as the execution runtime.

The old Symphony idea still maps conceptually to the system:
- Linear issue -> work item
- branch/worktree -> isolated environment
- coding agent -> ACP Codex session
- PR -> delivery artifact

But the concrete runtime is now OpenClaw ACP orchestration.

---

## Prerequisites

- A project scaffolded from Symphony Forge
- A Linear workspace with API access
- A GitHub repo with Actions enabled
- OpenClaw Gateway configured with:
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

## Step 2: Configure OpenClaw ACP

`openclaw acp` is the bridge. `acpx` is the coding runtime backend.

Recommended shape:
- OpenClaw `main` orchestrates planning, decomposition, review, and tracker sync
- ACP `codex` sessions implement feature tasks
- after verification, the parent Codex session spawns `quality-reviewer`, `performance-reviewer`, and `security-reviewer`
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

## Step 4: Configure Factory State

Each repo keeps run state under `.factory/`:
- `run.json`
- `verify.json`
- `reviews/*.json`

Initialize a run with:

```bash
python3 .codex/scripts/intake.py --issue ENG-123 --title "Feature title"
```

---

## Step 5: Human Approval Points

The factory is not fully autonomous.

Required human approval points:
1. after planning
2. before merge

Everything else can be handled by the factory loop.
