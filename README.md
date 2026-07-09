# Symphony Forge

Production system for building applications from in-repo architecture documents using **Claude Code coordination** and **Codex execution**, with optional **OpenClaw ACPX** orchestration.

## What This Is

Symphony Forge turns architecture docs, decisions, and product briefs already present in the target repo into shipped software. Claude Code coordinates discovery, planning, decisions, and orchestration through `codex-plugin-cc`, delegating planning-time codebase exploration to Codex read-only runs. Codex executes exploration, implementation, testing, and review.

- **Discovery** — structured intake that drives toward a precise, buildable spec
- **Harness** — architecture conventions and scaffold prompts that agents follow to generate fresh projects
- **Factory** — a doc-driven delivery loop that plans, decomposes, implements, tests, reviews, and prepares PRs with deterministic guardrails

## Structure

```text
symphony-forge/
├── .agents/                        # Shared prompts and deterministic scripts
├── .claude/                        # Claude Code adapter docs/settings
├── .codex/                         # Codex config, hooks, and agent registrations
├── .factory/                       # Machine-readable run state for feature execution
├── .github/workflows/              # Template workflow checks
├── constitution/                   # Engineering standards canon
├── docs/                           # Setup guides, factory contract, architecture/decision inputs
├── harness/nestjs-react/           # Scaffold prompt + conventions
├── harness.yaml                    # Runtime precedence and phase map
├── plans/                          # Active, completed, and debt plans
└── WORKFLOW.md                     # Linear <-> GitHub <-> run-artifact contract
```

## How It Works

### 1. Put the docs in the repo

The generated application repo is the system of record. Put architecture and decision docs directly under `docs/architecture/` and `docs/decisions/` before planning.
Also define product intent in `docs/product/BRIEF.md`.

### 2. Planning and decomposition

Use Claude Code for planning coordination. It delegates codebase exploration to Codex read-only runs, produces a decision-complete plan, then generates a Linear-first task graph from the in-repo docs. Human approval is required before implementation.

### 3. Implementation

Codex handles implementation at medium reasoning by default. The repo works in plain Codex mode or OpenClaw + ACP/ACPX mode.

### 4. Test and verify

Run the `automated-tester` subagent before deterministic verify. After review, run the `functional-checker` subagent for user-visible validation.

Deterministic validation still runs via:

```bash
python3 .agents/scripts/verify.py
```

### 5. Review

Spawn separate Codex review subagents for:
- code quality
- performance
- security

Each review outputs a score, blockers, residual risks, and a merge recommendation.

### 6. PR ready

GitHub gets the PR package. Linear stays the source of truth. Merge remains manual.

## Why This Shape

- The harness stays fresh — no frozen app template rot.
- Runtime hooks enforce deterministic behavior at phase gates.
- OpenClaw ACPX is available for orchestration, but not required for normal repo use.
- Codex custom subagents keep implementation support, testing, and review isolated.
- Claude Code stays thin-context by pushing code exploration and execution into Codex.

## Docs

- [Codex Factory](docs/codex-factory.md)
- [Factory Contract](docs/FACTORY.md)
- [Quality Contract](docs/QUALITY.md)
- [Product Brief Contract](docs/product/README.md)
- [Architecture Docs Contract](docs/architecture/README.md)
- [Decision Docs Contract](docs/decisions/README.md)
- [Harness Philosophy](docs/harness-philosophy.md)
- [Validation Loop](docs/validation-loop.md)
- [Symphony Setup](docs/symphony-setup.md)
- [Getting Started](docs/getting-started.md)
- [Degraded Mode](docs/degraded-mode.md)
