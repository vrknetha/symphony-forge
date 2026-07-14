# Forge — harness operations (canonical body, both runtimes)

Canon lives in `AGENTS.md`, `WORKFLOW.md`, and `harness.yaml`. This skill only
routes to it.

**The contract: devs speak intents; you run the mapped command and report its
output.** A dev should never need to type a `python3 .agents/scripts/...`
command themselves. Prompts are the interface, recorder commands are the
contract — every artifact you record must match its `.agents/schemas/` file,
including `generated_by`. The one exception is human-only actions
(`decision accept`): relay the command, never run it.

`./forge <cmd>` (from repo root) is shorthand for
`python3 .agents/scripts/forge.py <cmd>` — either form works everywhere below.

## ALWAYS start here

```bash
./forge next
```

That is the deterministic phase engine — it reads run state, the context
ledger, plans, the roadmap, and artifacts, and prints where the project is and
the exact next actions. Never guess the phase yourself; run it, then execute
or route:

| `next` says | Do |
|---|---|
| discovery/prototype | gstack `/office-hours` for the discovery conversation; prototype freely |
| roadmap missing | run the project-level decomposition (`.agents/prompts/decomposer.md`), then `./forge roadmap import --input <json>` |
| planning | plan per `.agents/prompts/planner.md` (Claude plan mode default, `planner-high` Codex agent alternate); exploration read-only via Codex |
| decomposing | run docs-decomposer per task, record with `record_decomposition_from_json.py` (schema incl. `user_facing`) |
| implementing | delegate the leaf task (Claude: `/codex:rescue --background`; Codex: `.agents/prompts/implementer.md`) — the implementer writes and records the tests; user-facing tasks MUST load + attest emil-design-eng + frontend-design in `skills_used` (recorder-enforced; harness.yaml `required_skills`) |
| verifying | `python3 .agents/scripts/verify.py` |
| reviewing | ONE autoreview run in Codex, three lenses (`.agents/prompts/reviewer.md`) |
| functional-check | only shown when the task is user-facing; run `functional-checker` |
| harvest pending | follow `.agents/prompts/harvester.md` |
| anything with a command | run the command verbatim |

## Route by intent

| Dev says | Do |
|---|---|
| set up my machine | `./forge doctor` (`--fix` installs the toolchain; logins stay manual) |
| create a new project | `./forge init --name <project> --target <dir>` (or the `knacklabs-new-project` skill) |
| migrate an existing repo into the harness | `knacklabs-migrate-project` skill — core: `./forge adopt --target <repo>` from the harness clone (clean tree; old AGENTS/CLAUDE preserved to docs/context/) |
| migrate my gstack history / gstack outputs are on my machine | `./forge gstack migrate` — union-merges ~/.gstack/projects/<slug>/ into the repo's .gstack/ (then commit). Going forward .envrc + `direnv allow` keeps gstack in-repo |
| what's left to build / show the roadmap | `./forge roadmap list` (`--pending` for what's next; grouped by epic, shows @assignee) |
| grill the handover / stress-test before a gate | `.agents/prompts/griller.md` — one question at a time vs the actual docs; resolve findings; record `record_grill_from_json.py --gate signoff\|epics`. Sign-off and roadmap import REFUSE without a fresh pass |
| PM approves the epics | `./forge decision new epics-approved` — THE PM runs the accept; roadmap import is refused without it (and without a passing epics grill) |
| here's the project backlog / handoff decomposition | `./forge roadmap import --input <json>` (epics + stories w/ acceptance_criteria + skill) |
| add a story to the roadmap | `./forge roadmap add <KEY> "<title>" --epic <epic> --skill frontend\|backend\|fullstack` |
| define the team / who's on this project | `./forge team set <handle> --role dev --skills frontend,backend` (optional roster; `./forge team list`) |
| assign a story / distribute work (EM) | `./forge roadmap assign <KEY> --to <dev>` — checked against the roster; match story skill to dev skills |
| who does what / role handoffs | `docs/ROLES.md` — forge next tags every step [PM]/[EM]/[dev] |
| start a task / new feature | `python3 .agents/scripts/intake.py --issue <KEY> --title "<title>"` — then check `forge.py context list --pending` BEFORE planning |
| plan is approved | `python3 .agents/scripts/forge.py plan save --from <plan-file>` (plan must follow `.agents/prompts/planner.md`, incl. Decisions section) |
| record the decomposition | `python3 .agents/scripts/record_decomposition_from_json.py --input <json>`, then `update_run.py --phase implementing --decomposition-status recorded` |
| record a decision | `./forge decision new <slug>` — draft only |
| human confirms a decision | THE HUMAN runs `./forge decision accept <slug> --by "Name"` — never you; relay the command and wait |
| made an assumption while implementing | `python3 .agents/scripts/forge.py plan assume "<one sentence>"` — lands on the active plan AND as an open row in plans/assumptions.md |
| review / guide the assumptions (orchestrator) | `./forge assumptions list --open`, then `./forge assumptions resolve <id> --status confirmed\|fix-needed\|promoted --notes "..."` — pr_ready refuses unguided rows |
| record the test results | `python3 .agents/scripts/record_test_from_json.py --kind automated\|functional --input <json>` |
| run verify / does it build | `python3 .agents/scripts/verify.py` (never bypass with ad hoc commands) |
| record the review | `python3 .agents/scripts/record_review_from_json.py --aspect quality\|performance\|security --input <json>` |
| client signed off | `python3 .agents/scripts/record_signoff.py` |
| harvest context / process the dump | follow `.agents/prompts/harvester.md`, then `forge.py context mark ...` |
| harness status | read `.factory/run.json`; `forge.py context list --pending`; `ls .agents/skills/proposed/` |
| is this PR ready | `python3 .agents/scripts/pr_ready.py` (never bypass with ad hoc checks) |
| mine for skills / retro | follow `.agents/prompts/skill-miner.md` |
| improve the animations / motion audit | run the `improve-animations` skill (read-only audit → prioritized plans); land its items via `./forge roadmap add` or a task intake — never apply fixes straight from the audit |
| update a client repo to the latest harness | from the HARNESS clone: `./forge upgrade --target <client-repo>` (clean tree required; review the diff, run the linter + gate tests, commit) |

## Hard rules

- Implementation is delegated to Codex; planning exploration is Codex
  read-only. See `harness.yaml` for phase owners — it is the ALLOWLIST;
  recorders refuse artifacts from unpinned generators.
- Review is ONE autoreview run — never inline, never nested reviewers.
- Never set a decision to `accepted`, never flip `client_signoff`, never
  activate a proposed skill — humans do those.
- If `check_dual_runtime.py` fails, fix the violation it names before anything else.
