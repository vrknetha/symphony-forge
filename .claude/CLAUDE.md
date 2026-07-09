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

- Delegate implementation with `/codex:rescue --background`.
- Review with `/codex:review` / `/codex:adversarial-review` at the review phase.
- The Stop-hook review gate must stay DISABLED (`/codex:setup --disable-review-gate`).
- If the plugin is unavailable, follow `docs/degraded-mode.md`.

## Ground rules

- Per-task planning happens HERE, in plan mode (contract: `.agents/prompts/planner.md`,
  including the mandatory Decisions section). Approval is not real until the plan
  is in-repo: `python3 .agents/scripts/forge.py plan save --from <plan-file>`.
- Decisions land in `docs/decisions/` via `python3 .agents/scripts/forge.py decision new <slug>`.
- Phases ≥ planning require client sign-off (`python3 .agents/scripts/record_signoff.py`).
- `python3 .agents/scripts/check_dual_runtime.py` must stay green.
- gstack `/codex` and `/ship` are disabled in factory repos (see `harness.yaml`).
