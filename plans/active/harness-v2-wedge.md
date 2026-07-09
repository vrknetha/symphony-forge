# Plan: Harness v2 Week-One Wedge

Status: approved (design: office-hours session 2026-07-09, decisions D8–D16)
Branch: feature/harness-v2-wedge

## Problem

Symphony Forge is Codex-only and starts at "docs already in repo". Turn it into the dual-runtime (Claude Code coordinator + Codex executor) harness with an `.agents/`-centered layout, a repo bootstrap CLI, a client-sign-off gate, de-noised hooks, and structural linting — per the approved v2 design.

## Scope / Non-goals

In scope: the 7 work items below, all inside this repo.
Non-goals: skill-pack installation logic, OpenClaw changes, decision-exhaust automation, template-sync to generated repos, Linear scripts changes, nx workspace generation (forge init lays the harness skeleton and points at the scaffold prompt; it does NOT run npx).

## Work Items

### 1. `.agents/`-centered layout
- `git mv .codex/prompts .agents/prompts` and `git mv .codex/scripts .agents/scripts`.
- `.codex/` keeps ONLY: `config.toml`, `hooks.json`, `agents/*.toml` (runtime registration format — inline `developer_instructions` are acceptable there; they are registration config).
- Update `.codex/hooks.json` commands to `.agents/scripts/...` and remove the hooks deleted in item 2.
- Fix every `.codex/scripts/` path reference across the repo: `AGENTS.md`, `WORKFLOW.md`, `docs/FACTORY.md`, `docs/codex-factory.md`, other docs, `.github/workflows/factory-scaffold.yml`, and any intra-script references (e.g. `pre_tool_use.py` mentions `.codex/scripts/verify.py`).
- Add `.claude/CLAUDE.md`: a thin pointer (< 40 lines) — read AGENTS.md first, mandatory read order, "codebase exploration during planning is delegated to Codex via /codex:rescue (read-only)", codex-plugin-cc usage note (review gate must stay disabled), pointer to `harness.yaml` and `docs/degraded-mode.md`. No standards content — reference only, e.g. `<!-- canon: AGENTS.md -->`.

### 2. Hook de-noising (principle: quiet by default, loud only at phase gates)
- `session_start.py`: keep ONLY the dynamic run-state lines (issue, phase, plan status, decomposition status). Delete the 4 static context lines (they restate AGENTS.md).
- Delete `user_prompt_submit.py` and its hooks.json entry entirely (keyword sniffing has false positives both ways; phase enforcement lives in the pre-tool gate and update_run.py).
- Delete `post_tool_use.py` and its hooks.json entry entirely (per-command context injection is noise; block-on-any-non-zero-exit blocks legitimate grep/probe commands; the transcript already records history).
- `stop_continue.py`: replace all blocking logic with: if run state exists and phase == "implementing" → emit a single NON-blocking one-line warning ("phase is implementing; artifacts incomplete — pr_ready.py is the gate"), else `{"continue": true}`. Never `"decision": "block"`. (pr_ready.py already gates deterministically.)
- `pre_tool_use.py`: keep destructive-command policy and verify-bypass rule (update path to `.agents/scripts/verify.py`); ADD the sign-off gate: if `.factory/run.json` exists, `client_signoff` is not true, and the command invokes phase-advancing scripts (`update_run.py --phase` with a phase ≥ planning, or `record_decomposition_from_json.py`, or `pr_ready.py`) → deny with reason "client sign-off not recorded; run .agents/scripts/record_signoff.py after docs/decisions/NNNN-client-signoff.md is accepted". Also remove the noisy success `systemMessage` ("Factory policy check passed" on every command) — print `{}` or nothing on pass, per the hook contract.

### 3. `forge` CLI — `.agents/scripts/forge.py` (argparse or typer if available; stdlib-only preferred, match existing script style)
- `forge.py init --name <project> [--target <dir>] [--stack nestjs-react] [--force]`:
  - Target dir must be empty/nonexistent unless `--force`. No merge mode.
  - Creates: `AGENTS.md` (from a template modeled on this repo's, project-name substituted), `.agents/{prompts,scripts}` (copied from this repo), `.codex/{config.toml,hooks.json,agents/}` (copied), `.claude/CLAUDE.md` (copied), `constitution/` (vendored copy, pinned — add a `constitution/VENDORED_FROM` line with source repo+commit), `harness.yaml` (copied), `docs/product/BRIEF.md` (from `harness/nestjs-react/BRIEF_TEMPLATE.md`), `docs/architecture/README.md` + `docs/decisions/README.md` (copied contracts), `docs/decisions/` empty, `plans/{active,completed,debt}/`, `.factory/` with minimal `run.json`: `{"project": <name>, "client_signoff": false, "created_at": iso}`, `.github/workflows/factory-scaffold.yml` (copied), `.gitignore` (copied), and a phase-0a discovery template `docs/product/DISCOVERY.md` (problem, stakeholders, client-approved decisions checklist).
  - Prints next steps (fill discovery → get sign-off → record_signoff.py → nx scaffold via harness/nestjs-react/SCAFFOLD_PROMPT.md).
- `forge.py decision new <slug> [--title <t>]`: scans `docs/decisions/` for `NNNN-*.md`, allocates next integer (0001 if none), writes template with frontmatter `status: proposed`, `confirmed_by: ""`, `date: <today>`, body sections Context / Decision / Consequences. Prints the path and reminds that `status: accepted` requires non-empty `confirmed_by` and a `Confirmed-by:` git trailer on the commit.

### 4. Dual-runtime linter — `.agents/scripts/check_dual_runtime.py` (exit 0 clean / 1 violations; agent-readable error messages: file, rule, what to do instead — match harness-philosophy.md error style)
Checks (all structural):
- (a) canon exists: `AGENTS.md`, `docs/`, `constitution/` (≥1 .md), `.agents/prompts/`, `.agents/scripts/`, `harness.yaml`.
- (b) forbidden basenames: no file under `.claude/` or `.codex/` shares a basename with any file in `constitution/` or `harness/*/conventions/`.
- (c) duplication: no file under `.claude/` or `.codex/` is a byte-copy of, or contains ≥10 consecutive identical non-blank lines from, any file in `constitution/`, `docs/`, or `harness/*/conventions/`.
- (d) canon markers: every `<!-- canon: <path> -->` occurrence anywhere in `.claude/` or `.codex/` must point at an existing repo-relative path.
- (e) decision records: every `docs/decisions/NNNN-*.md` has valid frontmatter; `status: accepted` requires non-empty `confirmed_by`; NNNN numbers unique. If the file is committed, its adding commit should contain a `Confirmed-by:` trailer — check via `git log --diff-filter=A --format=%B -- <file>`; WARN (not fail) when git history is unavailable (fresh scaffold).
- (f) path parity: `.claude/CLAUDE.md` must reference `AGENTS.md`; `.codex/hooks.json` commands must point into `.agents/scripts/` and referenced scripts must exist.
- (g) thin-adapter rule: `.claude/` may contain only `CLAUDE.md` (≤ 40 lines) and `settings.json`; `.codex/` may contain only `config.toml`, `hooks.json`, `agents/*.toml`. Any other file (or any `.py`/prompt `.md` under runtime dirs) is a violation directing it to `.agents/`.
Run it against THIS repo and make this repo pass.

### 5. `harness.yaml` (repo root) + sign-off machinery
- `harness.yaml`: `version: 1`; `precedence: [constitution, factory-gates, gstack, other-skills]`; `phases:` — `discovery` (owner `gstack:/office-hours`, notes: lightweight, no .factory ceremony), `prototype` (owner `prototype-skill`, allowed: `ponytail:lite`), `planning` (owner `claude-code:plan-mode`, exploration: `codex:read-only` — the planner delegates all code exploration to Codex), `implementation` (owner `codex:/codex:rescue`, prompts: `.agents/prompts/implementer.md`), `testing` (owner `automated-tester` + `functional-checker`), `review` (owner `codex-subagents:quality,performance,security`, escalation: `openclaw:autoreview` for `security-sensitive|migration|cross-domain` flagged tasks at pr-ready, note: never both loops on one task), `ship` (owner `.agents/scripts/pr_ready.py`, merge: manual). `disabled_in_factory_repos: [gstack:/codex, gstack:/ship, codex-plugin-cc:stop-hook-review-gate]`; `not_installed_v1: [mattpocock/skills]`.
- `.agents/scripts/record_signoff.py`: finds `docs/decisions/*-client-signoff.md` (slug match, any NNNN); requires `status: accepted` + non-empty `confirmed_by`; sets `client_signoff: true` in `.factory/run.json` (creates minimal run.json if absent); clear agent-readable errors otherwise.
- `update_run.py`: refuse `--phase` values in {planning, decomposing, awaiting-approval, implementing, testing, reviewing, functional-check, pr-ready} when `client_signoff` is not true in run.json (error explains record_signoff.py). Phases `discovery`/`prototype`/`blocked`/`done` are allowed without sign-off.

### 6. Constitution wiring + degraded mode
- `constitution/*.md` already imported (20 files, committed on this branch by the coordinator). Add `constitution/README.md`: index table (adapt from the topic table in the old skill: topic → read when → file), the precedence rule (constitution wins over any skill guidance; gstack over other third-party), and: "This directory is the single source of truth for CAW engineering standards. The former Notion pages are deprecated; changes land only as PRs to this repo. Deviations must be deliberate and stated."
- Reconcile the single-source rule: for each `harness/nestjs-react/conventions/*.md` that overlaps a constitution topic, add a one-line header `> Canon: see <!-- canon: constitution/<file> --> — this file only adds NestJS-React-scaffold specifics.` Do NOT rewrite their content in this pass.
- `docs/degraded-mode.md`: what a dev does when codex-plugin-cc is unavailable — run the same phase prompts directly via `codex exec` (examples for exploration: `codex exec -s read-only "<question>"`; implementation: `codex exec` with `.agents/prompts/implementer.md` + the task; review: the three subagents), artifacts identical, gates unchanged. Short, command-first.

### 7. Docs + CI
- `README.md` + `AGENTS.md`: update structure map (.agents/, constitution/, harness.yaml, .claude/), replace "Codex as the primary developers" framing with the two-plane model (Claude Code coordinates + plans, exploration delegated to Codex read-only; Codex implements/tests/reviews), add harness.yaml + constitution/README.md to the mandatory read order. Keep AGENTS.md near 100 lines.
- `WORKFLOW.md`/`docs/FACTORY.md`/`docs/codex-factory.md`: path updates + add phases `discovery` and `prototype` before `planning` (lightweight, sign-off gate between prototype and planning).
- `.github/workflows/factory-scaffold.yml`: update paths; add steps: run `.agents/scripts/check_dual_runtime.py` on the repo; smoke test — `python3 .agents/scripts/forge.py init --name smoke --target /tmp/forge-smoke` then run `check_dual_runtime.py` and `check_factory_scaffold.py` against the generated dir (adjust check_factory_scaffold.py invocation to accept a target dir if needed).

## Acceptance Criteria
- [ ] `python3 -m compileall .agents/scripts` clean
- [ ] `python3 .agents/scripts/check_dual_runtime.py` exits 0 on this repo
- [ ] `forge.py init` into a temp dir succeeds; linter + scaffold check pass on the result; re-run without `--force` fails cleanly
- [ ] `forge.py decision new test-slug` allocates 0001, then 0002 on second run (in the temp scaffold)
- [ ] `record_signoff.py` fails without an accepted client-signoff record, succeeds with one; `update_run.py --phase planning` refuses before sign-off, works after
- [ ] hooks.json references only existing `.agents/scripts/` files; deleted hooks are gone
- [ ] `check_agents_hygiene.py` still passes (AGENTS.md size + links)
- [ ] no doc references `.codex/scripts/` anywhere (grep clean)

## Verify Plan
Run the acceptance criteria commands; commit in logical units on this branch with conventional-commit messages.
