# Symphony Forge

CAW's harness for building client applications with **Claude Code coordination** and **Codex execution** — from discovery and client sign-off through scaffolding, per-feature delivery, and a self-evolving record of every decision.

## Quick Start (devs)

One-time machine setup, then everything is conversation:

```bash
git clone git@github.com:cawstudios/symphony-forge.git
cd symphony-forge && ./setup
```

Then, in Claude Code:

> **"Set up a new CAW project called my-app"**

The `caw-new-project` skill updates the harness, runs `doctor` (and fixes what it can), scaffolds the repo with `forge init`, and hands you to the project's own `/forge` skill. From then on, **ask "what now?" in any phase** — `/forge` runs the deterministic `forge.py next` engine and routes you (same answer for Codex sessions via `AGENTS.md`). Manual equivalents for every step: [Getting Started](docs/getting-started.md).

## The Lifecycle

```text
0a discovery ──▶ 0b prototype ──▶ CLIENT SIGN-OFF ──▶ scaffold (nx)
                                     (hard gate)          │
      ┌───────────────────────────────────────────────────┘
      ▼
  per feature:  intake ▶ plan ▶ decompose ▶ implement ▶ test ▶ verify ▶ review ▶ PR
                        (Claude)  (Codex)     (Codex)                 (subagents)
```

- **Before sign-off**: lightweight on purpose — no ceremony. Discovery via gstack `/office-hours`, prototypes are throwaway.
- **After sign-off**: deterministic gates. Plans live in `plans/`, decisions in `docs/decisions/`, evidence in `.factory/`; `pr_ready.py` archives every shipped task's plan + proof to `plans/completed/` and `.factory/history/`.
- **Continuously**: dump raw context (client emails, transcripts) into `docs/context/` — a ledger tracks harvest status, and agents turn pending files into proposed decisions and doc updates. Dev corrections get mined into proposed skills (`.agents/skills/proposed/`) that humans promote.

Phase ownership — which tool runs which phase — is declared in [`harness.yaml`](harness.yaml).

## Structure

```text
symphony-forge/
├── .agents/                        # Shared substance: prompts, deterministic scripts, proposed skills
├── .claude/                        # Claude Code adapter + /forge skill (thin, linter-enforced)
├── .codex/                         # Codex adapter: config, hooks, agent registrations (thin)
├── .factory/                       # Run state + per-task history archive
├── .github/workflows/              # Scaffold checks, dual-runtime lint, daily gardener
├── constitution/                   # CAW engineering standards — THE single source of truth
├── docs/                           # Contracts, guides, decisions, context inbox
├── harness/nestjs-react/           # Scaffold prompt + stack conventions
├── harness.yaml                    # Phase ownership + skill precedence manifest
├── plans/                          # Active and completed task plans
├── AGENTS.md                       # The agent contract (both runtimes)
└── CLAUDE.md                       # Import shim: @AGENTS.md + @.claude/CLAUDE.md
```

## Why This Shape

- **One canon, two runtimes.** Standards live once (`constitution/`, `AGENTS.md`, `harness.yaml`); `.claude/` and `.codex/` are thin adapters. `check_dual_runtime.py` fails CI on any duplication.
- **Gates at phase transitions, not keystrokes.** Hooks are quiet; `record_signoff.py`, `update_run.py`, and `pr_ready.py` are the deterministic gates. Unapproved work can't ship.
- **Decisions are exhaust, never forms.** Planning forces a Decisions section; harvesting turns raw context into records; humans confirm every `accepted`.
- **Evolution is curated.** Recurring corrections become *proposed* skills and constitution PRs; nothing self-activates.
- **One owner per phase.** Overlapping skills (gstack `/ship`, ponytail in factory code, nested reviewers) are explicitly disabled in `harness.yaml`.

## Docs

- [Getting Started](docs/getting-started.md) — the blessed path, step by step
- [Workflow Contract](WORKFLOW.md) — phases, gates, artifacts, evolution loop
- [Factory Contract](docs/FACTORY.md) · [Quality Contract](docs/QUALITY.md)
- [Constitution](constitution/README.md) — engineering standards index
- [Harness Philosophy](docs/harness-philosophy.md) · [Validation Loop](docs/validation-loop.md)
- [Product Brief](docs/product/README.md) · [Architecture](docs/architecture/README.md) · [Decisions](docs/decisions/README.md)
- [Context Inbox](docs/context/README.md) — dump files here, harvest tracked
- [Degraded Mode](docs/degraded-mode.md) — when codex-plugin-cc is unavailable
- [Codex Factory](docs/codex-factory.md) · [Symphony Setup](docs/symphony-setup.md)
