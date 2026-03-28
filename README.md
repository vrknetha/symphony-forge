# Symphony Forge

Production system for building client software using **Codex + OpenClaw ACPX** and harness engineering.

## What This Is

Symphony Forge turns client ideas into shipped software using AI agents as the primary developers. It provides:

- **Discovery** — a structured intake process that drives toward a precise, buildable spec
- **Harness** — architecture conventions and scaffold prompts that agents follow to generate fresh projects
- **Factory** — a Codex/OpenClaw delivery loop that plans, implements, verifies, reviews, and prepares PRs with deterministic guardrails

## Structure

```text
symphony-forge/
├── .codex/                         # Codex config, hooks, agents, prompts, deterministic scripts
├── .factory/                       # Machine-readable run state for feature execution
├── .github/workflows/              # Template workflow checks
├── harness/nestjs-react/           # Scaffold prompt + conventions
├── plans/                          # Active, completed, and debt plans
├── projects/                       # Per-client project briefs
├── docs/                           # Setup guides and operating model
└── WORKFLOW.md                     # Linear <-> GitHub <-> ACP phase contract
```

## How It Works

### 1. Discovery

Capture the feature or project as a brief. The output is an issue and a durable plan context.

### 2. Planning

Use a high-reasoning model (`claude-opus-4-6` or `gpt-5.4`) to produce a decision-complete plan with acceptance criteria and decomposition. Human approval is required before implementation.

### 3. Implementation

OpenClaw `main` orchestrates. ACP/ACPX `codex` sessions implement bounded tasks in isolated worktrees and branches.

### 4. Verify

Run deterministic verification via:

```bash
python3 .codex/scripts/verify.py
```

### 5. Review

Spawn separate Codex review subagents for:
- code quality
- performance
- security

Each review outputs a score, blockers, residual risks, and a merge recommendation. The parent Codex session can persist structured results with `python3 .codex/scripts/record_review_from_json.py`.

### 6. PR Ready

GitHub gets the PR package. Linear stays the source of truth. Merge remains manual.

## Why This Shape

- The harness stays fresh — no frozen app template rot.
- Codex hooks enforce deterministic behavior at runtime.
- OpenClaw ACPX keeps coding work in persistent Codex sessions.
- Codex custom subagents keep review isolated and parallel.
- The coordinator stays thin-context by pushing coding work to ACP workers and review work to read-only subagents.

## Docs

- [Codex Factory](docs/codex-factory.md)
- [Harness Philosophy](docs/harness-philosophy.md)
- [Validation Loop](docs/validation-loop.md)
- [Symphony Setup](docs/symphony-setup.md)
- [Getting Started](docs/getting-started.md)
