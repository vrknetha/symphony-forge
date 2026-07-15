# Claude Code adapter — Symphony Forge

<!-- canon: AGENTS.md -->
Read `AGENTS.md` first; it is the contract. Standards live in `constitution/`
(<!-- canon: constitution/README.md -->) and phase ownership in `harness.yaml`.

## Role split (enforced)

- Claude Code coordinates: discovery, planning, decisions, orchestration.
- Codex executes: exploration, implementation, testing, review.
- During planning, do NOT grep/read application code yourself — delegate
  exploration to Codex read-only runs:
  `codex exec --profile explore -s read-only "<question>"`
  (gpt-5.6-terra @ high, .codex/explore.config.toml) and plan from the findings.

## codex-plugin-cc

- Delegate implementation with `/codex:rescue --background` — it runs
  `gpt-5.6-sol` at `medium` reasoning (.codex/config.toml); escalate effort
  to `high` for migrations/cross-domain/concurrency/security-sensitive work.
- Review = ONE autoreview run in Codex, three lenses (`.agents/prompts/reviewer.md`).
- The Stop-hook review gate must stay DISABLED (`/codex:setup --disable-review-gate`).
- If the plugin is unavailable, follow `docs/degraded-mode.md`.

## Ground rules

- Per-task planning is MANDATORY and happens in PLAN MODE here (contract:
  `.agents/prompts/planner.md`, incl. the mandatory Decisions section); the
  PreToolUse hook blocks product-code edits and non-read-only codex exec
  while the task is unplanned — do not fight it, switch to plan mode. Codex
  `planner-high` is the sanctioned alternative — same contract. Approval is
  not real until the plan is in-repo:
  `python3 .agents/scripts/forge.py plan save --from <plan-file>`.
- Decisions land in `docs/decisions/` via `./forge decision new <slug>`; only a
  HUMAN runs `./forge decision accept <slug> --by "Name"`.
- Phases ≥ planning require client sign-off (`python3 .agents/scripts/record_signoff.py`).
- `python3 .agents/scripts/check_dual_runtime.py` must stay green.
- gstack `/codex` and `/ship` are disabled in factory repos (see `harness.yaml`).
