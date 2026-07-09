# Forge — harness operations (canonical body, both runtimes)

Canon lives in `AGENTS.md`, `WORKFLOW.md`, and `harness.yaml`. This skill only
routes to it.

`./forge <cmd>` (from repo root) is shorthand for
`python3 .agents/scripts/forge.py <cmd>` — either form works everywhere below.

## ALWAYS start here

```bash
./forge next
```

That is the deterministic phase engine — it reads run state, the context
ledger, plans, and artifacts, and prints where the project is and the exact
next actions. Never guess the phase yourself; run it, then execute or route:

| `next` says | Do |
|---|---|
| discovery/prototype | gstack `/office-hours` for the discovery conversation; prototype freely |
| planning | plan per `.agents/prompts/planner.md` (Claude plan mode default, `planner-high` Codex agent alternate); exploration read-only via Codex |
| implementing | delegate the leaf task (Claude: `/codex:rescue --background`; Codex: `.agents/prompts/implementer.md`) |
| reviewing | spawn the three review subagents; autoreview only for flagged escalations |
| harvest pending | follow `.agents/prompts/harvester.md` |
| anything with a command | run the command verbatim |

## Route by intent

| Dev says | Do |
|---|---|
| start a task / new feature | `python3 .agents/scripts/intake.py --issue <KEY> --title "<title>"` — then check `forge.py context list --pending` BEFORE planning |
| plan is approved | `python3 .agents/scripts/forge.py plan save --from <plan-file>` (plan must follow `.agents/prompts/planner.md`, incl. Decisions section) |
| record a decision | `./forge decision new <slug>` — draft only |
| human confirms a decision | THE HUMAN runs `./forge decision accept <slug> --by "Name"` — never you; relay the command and wait |
| made an assumption while implementing | `python3 .agents/scripts/forge.py plan assume "<one sentence>"` — dated, on the active plan, dev reviews before merge |
| client signed off | `python3 .agents/scripts/record_signoff.py` |
| harvest context / process the dump | follow `.agents/prompts/harvester.md`, then `forge.py context mark ...` |
| harness status | read `.factory/run.json`; `forge.py context list --pending`; `ls .agents/skills/proposed/` |
| is this PR ready | `python3 .agents/scripts/pr_ready.py` (never bypass with ad hoc checks) |
| mine for skills / retro | follow `.agents/prompts/skill-miner.md` |
| machine setup | `./forge doctor` (`--fix` installs the toolchain) |
| update a client repo to the latest harness | from the HARNESS clone: `./forge upgrade --target <client-repo>` (clean tree required; review the diff, run the linter + gate tests, commit) |

## Hard rules

- Implementation is delegated to Codex; planning exploration is Codex
  read-only. See `harness.yaml` for phase owners.
- Never set a decision to `accepted`, never flip `client_signoff`, never
  activate a proposed skill — humans do those.
- If `check_dual_runtime.py` fails, fix the violation it names before anything else.
