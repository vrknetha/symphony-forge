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

The `caw-new-project` skill updates the harness, runs `doctor --fix` (installs the toolchain; only logins stay manual), scaffolds the repo with `forge init`, and hands you to the project's own `/forge` skill. From then on, **ask "what now?" in any phase** — `/forge` runs the deterministic `./forge next` engine and routes you (same answer for Codex sessions via `AGENTS.md`). Manual equivalents for every step: [Getting Started](docs/getting-started.md).

## The Lifecycle

```text
0a discovery ──▶ 0b prototype ──▶ CLIENT SIGN-OFF ──▶ scaffold (nx) ──▶ roadmap
                                     (hard gate)                           │
      ┌────────────────────────────────────────────────────────────────────┘
      ▼
  per feature:  intake ▶ plan ▶ decompose ▶ implement+test ▶ verify ▶ review ▶ PR
                       (Claude)   (Codex)       (Codex)              (autoreview)
```

- **Before sign-off**: lightweight on purpose — no ceremony, no time-box. Discovery via gstack `/office-hours`; the prototype that earns sign-off is preserved in `prototype/` as the permanent UX reference.
- **After sign-off**: deterministic gates. Plans live in `plans/`, decisions in `docs/decisions/`, evidence in `.factory/`; `pr_ready.py` archives every shipped task's plan + proof to `plans/completed/` and `.factory/history/`.
- **Continuously**: dump raw context (client emails, transcripts, notes) into `docs/context/` — dumping is free, tracking is automatic. Say *"process the context dump"* and an agent scans it into the ledger, harvests it into proposed decisions and BRIEF/architecture updates, and marks each file. You can't miss pending context: it greets every session start, tops every `./forge next`, raises a daily `gardener` issue, and **blocks `plan save`** until harvested or explicitly ignored. Dev corrections get mined into proposed skills (`.agents/skills/proposed/`) that humans promote.

Phase ownership — which tool runs which phase — is declared in [`harness.yaml`](harness.yaml).

## Who Runs What (skills by stage)

`harness.yaml` is the ALLOWLIST — these are the only pinned tools per stage,
and recorders refuse evidence from anything else (`generated_by` is checked
against `.agents/schemas/`). Adopting a new tool = a PR here, never a local
choice.

| Stage | You say | Skill / agent invoked | Deterministic record |
|---|---|---|---|
| machine setup | "Set up my machine" | `caw-new-project` skill → `./forge doctor --fix` | doctor report |
| new project | "Set up a new CAW project called X" | `caw-new-project` skill → `./forge init` | scaffolded repo |
| existing repo | "Migrate this repo into the harness" | `caw-migrate-project` skill → `./forge adopt` | vendored machinery; old context → `docs/context/` |
| any phase, lost | "What now?" | `/forge` skill → `./forge next` | — |
| 0a discovery | "Let's run office hours" | gstack `/office-hours` | `docs/product/DISCOVERY.md`, `BRIEF.md`; design docs + decisions in `.gstack/projects/` (in-repo via `.envrc`) |
| 0b prototype | build freely | ponytail (lite) allowed | preserved under `prototype/` |
| sign-off | "The client signed off" | none — HUMAN runs `decision accept` | `record_signoff.py` → `run.json` |
| workspace | "Scaffold the workspace" | Codex `/codex:rescue` + `SCAFFOLD_PROMPT.md` | nx workspace |
| roadmap (handoff) | "Build the project roadmap" | `docs-decomposer` (project-level) | `./forge roadmap import` → `plans/roadmap.json` |
| intake | "Start the next task on the roadmap" | `/forge` → `intake.py` | `.factory/run.json` |
| plan | "Plan this task" | Claude plan mode (or Codex `planner-high`); exploration via Codex read-only | `./forge plan save` → `plans/active/` |
| decompose | "Decompose it" | `docs-decomposer` | `record_decomposition_from_json.py` (incl. `user_facing`) |
| implement + test | "Implement it" | Codex `/codex:rescue --background` (implementer writes the tests) | `record_test_from_json.py --kind automated` |
| verify | "Run verify" | none — deterministic script | `verify.py` → `.factory/verify.json` |
| review | "Review it" | **autoreview** (ONE Codex run, three lenses) | `record_review_from_json.py` ×3 |
| functional check | only if `user_facing: true` | `functional-checker` subagent | `record_test_from_json.py --kind functional` |
| ship | "Is this PR ready?" | none — deterministic gate | `pr_ready.py` → archives + roadmap done |
| context dump | drop files in `docs/context/`, then "scan the context" | `/forge` → `./forge context scan` | `docs/context/ledger.json` |
| context harvest | "Process the context dump" | agent per `harvester.md` → proposed decisions + BRIEF edits | `./forge context mark --harvested\|--ignored` |
| retro / evolution | "Mine for skills" | agent per `skill-miner.md` + daily `gardener` workflow | proposals in `.agents/skills/proposed/` |

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
├── CLAUDE.md                       # Import shim: @AGENTS.md + @.claude/CLAUDE.md
└── forge                           # Dev entrypoint: ./forge next|init|doctor|decision|plan|context
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
