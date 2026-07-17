# Symphony Forge

KnackLabs's harness for building client applications with **Claude Code coordination** and **Codex execution** — from discovery and client sign-off through scaffolding, per-feature delivery, and a self-evolving record of every decision.

## Quick Start (devs)

One-time machine setup, then everything is conversation:

```bash
git clone git@github.com:knacklabs-ai/knacklabs-symphony-forge.git
cd symphony-forge && ./setup
```

Then, in Claude Code:

> **"Set up a new KnackLabs project called my-app"**

The `knacklabs-new-project` skill updates the harness, runs `doctor --fix` (installs the toolchain; only logins stay manual), scaffolds the repo with `forge init`, and hands you to the project's own `/forge` skill. From then on, **ask "what now?" in any phase** — `/forge` runs the deterministic `./forge next` engine and routes you (same answer for Codex sessions via `AGENTS.md`). Manual equivalents for every step: [Getting Started](docs/getting-started.md).

## The Lifecycle

```text
0a discovery ──▶ 0b prototype ──[GRILL]──▶ CLIENT SIGN-OFF ──▶ scaffold (nx) ──[GRILL]──▶ epics OK'd ──▶ roadmap + team
                                              (hard gate)                     (PM accept)                    │
      ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┘
      ▼
  per feature (own branch):
  intake ▶ PLAN MODE (forced) ▶ [GRILL] ▶ plan save ▶ decompose ▶ implement+test ▶ verify ▶ review ▶ [assumptions guided] ▶ PR
             (Claude)                                  (Codex)     (attested)              (autoreview)      (ship gate)
```

- **Before sign-off**: lightweight on purpose — no ceremony, no time-box. Discovery via gstack `/office-hours`; the prototype that earns sign-off is preserved in `prototype/` as the permanent UX reference.
- **After sign-off**: deterministic gates. Plans live in `plans/`, decisions in `docs/decisions/`, evidence in `.factory/`; `pr_ready.py` archives every shipped task's plan + proof to `plans/completed/` and `.factory/history/`.
- **Continuously**: dump raw context (client emails, transcripts, notes) into `docs/context/` — dumping is free, tracking is automatic. Say *"process the context dump"* and an agent scans it into the ledger, harvests it into proposed decisions and BRIEF/architecture updates, and marks each file. You can't miss pending context: it greets every session start, tops every `./forge next`, raises a daily `gardener` issue, and **blocks `plan save`** until harvested or explicitly ignored. Dev corrections get mined into proposed skills (`.agents/skills/proposed/`) that humans promote.

Phase ownership — which tool runs which phase — is declared in [`harness.yaml`](harness.yaml).

## The Gates

Every handoff is an artifact plus a deterministic gate; a gate you skipped is
a command that refuses. In lifecycle order:

| # | Gate | Refuses until | Enforced by |
|---|---|---|---|
| 1 | **Signoff grill** | an adversarial gaps/contradictions pass over DISCOVERY/BRIEF/decisions is recorded — fresh (docs unchanged since) and `pass` | `record_signoff.py` |
| 2 | **Client sign-off** | an accepted `client-signoff` decision names a human | `record_signoff.py`; every later phase checks the flag |
| 3 | **Epics grill + PM accept** | the epics/stories are grilled vs the BRIEF AND the PM accepts `epics-approved` | `forge roadmap import` (checks both, in order) |
| 4 | **Roster check** | assignees exist on `plans/team.json` (when a roster is defined) | `forge roadmap assign` |
| 5 | **Planning lock** | the active task has an approved, saved plan — until then product-code edits and writing Codex delegation are DENIED, with routing to PLAN MODE | PreToolUse hook (decision 0004 — the one sanctioned keystroke gate) |
| 6 | **Rescue-only invocation** | always: raw `codex exec` is denied in every phase, no escape hatch — `/codex:rescue` is the runtime | PreToolUse hook |
| 7 | **Plan grill** | the draft plan survives `/grill-me` vs the story's acceptance criteria + active decisions — same-issue, fresh, `pass` | `forge plan save` |
| 8 | **Pending context** | every `docs/context/` dump is harvested or explicitly ignored (and scans REFUSE secrets/oversize files outright) | `forge plan save`; `context scan` |
| 9 | **Schema + generator + skill attestation** | every evidence payload matches its `.agents/schemas/` file: `generated_by` on the allowlist, mandatory design skills attested in `skills_used` on user-facing artifacts | every `record_*` script |
| 10 | **Assumptions guided** | every `forge plan assume` row for the task is confirmed/promoted by the orchestrator (`fix-needed` keeps blocking) | `pr_ready.py` |
| 11 | **Ship gate** | approved plan, decomposition, verify OK, tests + 3 reviews ≥ 8 with no blockers, functional when `user_facing`, all evidence commit-stamped, same-commit, fresh | `pr_ready.py` — archives to `.factory/history/`, marks the roadmap item done |
| 12 | **Hygiene floor** | decision lifecycle intact (supersede links resolve, accepted records have substance), no prototype/ imports, schemas match harness.yaml, repo within size budgets | `check_dual_runtime.py` + `check_repo_budget.py` in CI |

Human-only, always: `decision accept` (sign-off, epics, promotions) — agents
relay the command and wait.

## Who Runs What (skills by stage)

`harness.yaml` is the ALLOWLIST — these are the only pinned tools per stage,
and recorders refuse evidence from anything else (`generated_by` is checked
against `.agents/schemas/`). Adopting a new tool = a PR here, never a local
choice.

| Stage | You say | Skill / agent invoked | Deterministic record |
|---|---|---|---|
| machine setup | "Set up my machine" | `knacklabs-new-project` skill → `./forge doctor --fix` | doctor report |
| new project | "Set up a new KnackLabs project called X" | `knacklabs-new-project` skill → `./forge init` | scaffolded repo |
| existing repo | "Migrate this repo into the harness" | `knacklabs-migrate-project` skill → `./forge adopt` | vendored machinery; old context → `docs/context/` |
| any phase, lost | "What now?" | `/forge` skill → `./forge next` | — |
| 0a discovery | "Let's run office hours" | gstack `/office-hours` | `docs/product/DISCOVERY.md`, `BRIEF.md`; design docs + decisions in `.gstack/projects/` (in-repo via `.envrc`) |
| 0b prototype | build freely | ponytail (lite) allowed | preserved under `prototype/` |
| grills (every gate) | "Grill the handover" / "Grill the epics" / "Grill me on this plan" | `griller` contract; `/grill-me` satisfies the plan gate | `record_grill_from_json.py` → `.factory/grills/`; sign-off, roadmap import, AND plan save refuse without a fresh pass |
| sign-off | "The client signed off" | none — HUMAN runs `decision accept` | `record_signoff.py` → `run.json` |
| workspace | "Scaffold the workspace" | Codex `/codex:rescue` + `SCAFFOLD_PROMPT.md` | nx workspace |
| epics (PM) | "Build the project roadmap" | `docs-decomposer` proposes; PM accepts `epics-approved` | epics in `plans/roadmap.json`; import gated on the accept |
| stories + distribution (EM) | "Record the backlog", "assign ENG-101 to alice" | `./forge roadmap import` / `assign` / `team set` | stories w/ acceptance criteria, `@assignee` (roster-checked) |
| intake | "Start the next task on the roadmap" | `/forge` → `intake.py` | `.factory/run.json` |
| plan | "Plan this task" | Claude PLAN MODE — forced by the hook (or Codex `planner-high`); exploration ONLY via `/codex:rescue --model gpt-5.6-terra --effort high`, read-only | grilled plan → `./forge plan save` → `plans/active/` |
| decompose | "Decompose it" | `docs-decomposer` | `record_decomposition_from_json.py` (incl. `user_facing`) |
| implement + test | "Implement it" | Codex `/codex:rescue --background` (implementer writes the tests); `user_facing` tasks MUST use `emil-design-eng` + `frontend-design` (attested in `skills_used`, enforced by the recorder) | `record_test_from_json.py --kind automated` |
| verify | "Run verify" | none — deterministic script | `verify.py` → `.factory/verify.json` |
| review | "Review it" | **autoreview** (ONE Codex run, three lenses) | `record_review_from_json.py` ×3 |
| functional check | only if `user_facing: true` | `functional-checker` subagent | `record_test_from_json.py --kind functional` |
| ship | "Is this PR ready?" | none — deterministic gate (refuses unguided assumptions, missing/stale evidence) | `pr_ready.py` → archives + roadmap done |
| guide assumptions (orchestrator) | "review the assumptions" | `./forge assumptions list --open` / `resolve` | `plans/assumptions.md` — ship gate reads it |
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
├── constitution/                   # KnackLabs engineering standards — THE single source of truth
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
- **Gates at phase transitions — plus exactly one keystroke gate.** Hooks are quiet by default; the deterministic gates (`record_signoff.py`, `record_*` recorders, `pr_ready.py`) do the enforcing. The one sanctioned exception (decision 0004): while a task is unplanned, the hook denies product-code edits and forces PLAN MODE. `/codex:rescue` is the only Codex invocation — raw `codex exec` is denied everywhere.
- **Grill before every handoff.** Sign-off, epics, and every task plan pass an adversarial gaps-and-contradictions interrogation whose recorded verdict the gate checks — stale or blocked grills don't open doors.
- **Evidence is attested, not asserted.** Every artifact carries `generated_by` (allowlist-checked) and `skills_used` (mandatory design skills enforced on user-facing work), stamped to the commit it attests.
- **Decisions are exhaust, never forms.** Planning forces a Decisions section; harvesting turns raw context into records; humans confirm every `accepted`; replacements go through `--supersedes`, and accepted records must have substance.
- **Garbage cannot become contract.** Secret/size guards at the inbox, repo budgets in CI, prototype-import ban, gstack noise gitignored, ledgers compacted, rejected proposals remembered.
- **Evolution is curated.** Recurring corrections become *proposed* skills and constitution PRs; nothing self-activates.
- **One owner per phase.** Overlapping skills (gstack `/ship`, ponytail in factory code, nested reviewers) are explicitly disabled in `harness.yaml`.

## Docs

- [Getting Started](docs/getting-started.md) — the blessed path, step by step
- [Roles](docs/ROLES.md) — PM / EM / dev: artifacts, phrases, approvals, handoffs
- [Workflow Contract](WORKFLOW.md) — phases, gates, grills, hygiene, evolution loop
- [Factory Contract](docs/FACTORY.md) · [Quality Contract](docs/QUALITY.md)
- [Constitution](constitution/README.md) — engineering standards index
- [Harness Philosophy](docs/harness-philosophy.md) · [Validation Loop](docs/validation-loop.md)
- [Product Brief](docs/product/README.md) · [Architecture](docs/architecture/README.md) · [Decisions](docs/decisions/README.md)
- [Context Inbox](docs/context/README.md) — dump files here, harvest tracked
- [Degraded Mode](docs/degraded-mode.md) — when codex-plugin-cc is unavailable
