# Codex Factory

Symphony Forge acts as a Codex/OpenClaw factory template.

## Runtime Model
- OpenClaw `main` orchestrates planning, decomposition, review, and tracker sync.
- ACP/ACPX `codex` sessions handle implementation.
- Codex custom subagents handle isolated review.
- Linear is the source of truth.
- GitHub mirrors implementation state and PR status.

## Why ACP/ACPX
OpenClaw documents ACP as the bridge for external coding runtimes and `acpx` as the runtime backend used for Codex-style coding sessions. That keeps implementation work in persistent coding contexts instead of bloating the coordinator session.

## Why Custom Review Subagents
Codex subagents are explicit, parallel, and configurable per role. Project-scoped agents under `.codex/agents/*.toml` let the implementation session fan out into narrow, read-only reviewers without mixing review concerns back into the implementation thread.

The default review set is:
- `quality-reviewer`
- `performance-reviewer`
- `security-reviewer`

All three are framework-independent and run on `gpt-5.3-codex` with `high` reasoning in `read-only` mode.

## Factory Directories
- `.codex/` — hooks, agents, prompts, and deterministic scripts
- `.factory/` — machine-readable run state
- `plans/` — durable plan history
- `projects/` — client or app briefs

## Golden Path
1. Run intake to initialize `.factory/run.json`
2. Produce and approve a plan
3. Start ACP Codex implementation session
4. Run deterministic verification
5. Spawn the three review subagents and wait for all results
6. Record quality / performance / security review artifacts, preferably via `record_review_from_json.py`
7. Mark PR ready and sync GitHub + Linear
