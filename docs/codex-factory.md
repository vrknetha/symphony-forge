# Dual-Runtime Factory

Symphony Forge is a doc-driven factory template where Claude Code coordinates planning and Codex executes exploration, implementation, testing, and review. OpenClaw orchestration is optional.

## Runtime Model
- Product intent lives in `docs/product/BRIEF.md`.
- Architecture and decision docs live in the repo before planning starts.
- Claude Code owns planning coordination and delegates codebase exploration to Codex read-only runs.
- Codex or OpenClaw + ACP/ACPX handles implementation.
- Codex custom subagents handle testing and isolated review.
- The repo's artifacts are the source of truth; a tracker (Linear, GitHub
  Issues, Jira) is an optional mirror.
- GitHub mirrors implementation state and PR status.

## Why ACP/ACPX Is Optional
OpenClaw ACP is useful for orchestration and long-running issue runs, but this template must also work in plain Codex without ACP.

## Why Custom Subagents
Codex subagents are explicit, parallel, and configurable per role. Project-scoped agents under `.codex/agents/*.toml` let the implementation session fan out into narrow specialists without mixing all concerns into one thread.

The default specialist set is:
- `planner-high`
- `docs-decomposer`
- `automated-tester`
- `functional-checker`
- `quality-reviewer`
- `performance-reviewer`
- `security-reviewer`

Reasoning policy:
- planning and decomposition: high
- implementation default: medium
- review and testing: explicit overrides

## Factory Directories
- `.agents/` — shared prompts and deterministic scripts
- `.codex/` — Codex config, hooks, and agent registrations
- `.claude/` — Claude Code adapter docs/settings
- `constitution/` — engineering standards canon
- `.factory/` — machine-readable run state
- `plans/` — durable plan history
- `docs/product/` — product intent and brief
- `docs/architecture/` and `docs/decisions/` — in-repo source of truth

## Golden Path
1. Run intake to initialize `.factory/run.json`
2. Review product, architecture, and decision docs
3. Produce and approve a plan
4. Record decomposition from the docs
5. Implement one bounded leaf task
6. Run automated testing and deterministic verify
7. Spawn the three review subagents and wait for all results
8. Run the functional checker
9. Mark PR ready (sync the tracker only if the project uses one)
