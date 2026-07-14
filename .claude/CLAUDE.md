# Claude Code adapter — Symphony Forge

<!-- canon: AGENTS.md -->
Read `AGENTS.md` first; it is the contract. Standards live in `constitution/`
(<!-- canon: constitution/README.md -->) and phase ownership in `harness.yaml`.

## Role split (enforced)

- Claude Code coordinates: discovery, planning, decisions, orchestration.
- Codex executes: exploration, implementation, testing, review.
- During planning, do NOT grep/read application code yourself — delegate
  exploration to Codex read-only runs (`/codex:rescue` or
  `codex exec -s read-only "<question>"`) and plan from the findings.

## codex-plugin-cc

- Delegate implementation with `/codex:rescue --background` — it runs
  `gpt-5.6-luna` at `xhigh` reasoning (.codex/config.toml); do not downgrade
  the effort, and escalate non-bounded tasks to a stronger tier instead.
- Review = ONE autoreview run in Codex, three lenses (`.agents/prompts/reviewer.md`).
- The Stop-hook review gate must stay DISABLED (`/codex:setup --disable-review-gate`).
- If the plugin is unavailable, follow `docs/degraded-mode.md`.

## Ground rules

- Per-task planning defaults to plan mode HERE (contract: `.agents/prompts/planner.md`,
  incl. the mandatory Decisions section); Codex `planner-high` is the sanctioned
  alternative — same contract. Approval is not real until the plan is in-repo:
  `python3 .agents/scripts/forge.py plan save --from <plan-file>`.
- Decisions land in `docs/decisions/` via `./forge decision new <slug>`; only a
  HUMAN runs `./forge decision accept <slug> --by "Name"`.
- Phases ≥ planning require client sign-off (`python3 .agents/scripts/record_signoff.py`).
- `python3 .agents/scripts/check_dual_runtime.py` must stay green.
- gstack `/codex` and `/ship` are disabled in factory repos (see `harness.yaml`).
