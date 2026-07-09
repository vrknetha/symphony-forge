# Getting Started with Symphony Forge

Symphony Forge is a dual-runtime harness plus doc-driven factory for building
agent-ready software. Claude Code coordinates; Codex executes. This page is the
one blessed path from empty directory to first feature PR.

**Agent-first shortcut:** after step 1's clone, run `./setup` once — it
installs the `caw-new-project` skill, and steps 2–3 become one sentence to
Claude Code: *"Set up a new CAW project called my-app."* The manual commands
below are the equivalents (and what the agent runs for you).

---

## 1. Get the harness (once per machine)

Clone it wherever you keep repos — `./setup` records the location for the
bootstrap skill:

```bash
git clone git@github.com:cawstudios/symphony-forge.git
cd symphony-forge
./setup
```

## 2. Check your machine

```bash
./forge doctor
```

Fix anything it reports — or let it: `doctor --fix` auto-installs everything
installable (Codex CLI via npm, codex-plugin-cc and ponytail via the
`claude plugin` CLI, gstack and autoreview from their GitHub repos). It
checks: git, Node 20+, pnpm, Docker, Codex CLI + login, Claude Code,
codex-plugin-cc, gstack, autoreview, and ponytail. Only logins (`codex
login`) stay manual. Re-run until it says `ready`.

## 3. Create your project

```bash
./forge init --name my-app --target ../my-app
cd ../my-app
```

This scaffolds a complete, git-initialized repo: dual-runtime adapters
(`.claude/`, `.codex/`), shared agent assets (`.agents/`), the vendored
engineering constitution (pinned in `constitution/VENDORED_FROM`), the phase
manifest (`harness.yaml`), doc contracts, and an armed sign-off gate. It fails
on a non-empty target; there is no merge mode.

> Do NOT create client projects with `gh repo create --template` — a template
> copy drags along the harness's own plans, run state, and history. The
> GitHub template flag exists for forking the harness itself, not for
> starting projects.

## 4. Discovery and prototype (phases 0a / 0b — lightweight on purpose)

1. Fill `docs/product/DISCOVERY.md` (problem, stakeholders, client-approved
   decisions). Use gstack `/office-hours` in Claude Code for the discovery
   conversation.
2. Fill `docs/product/BRIEF.md` (contract: `docs/product/README.md`).
3. Prototype freely — no `.factory` ceremony applies before sign-off.
4. Capture every client decision as a record:

```bash
./forge decision new <slug>
```

## 5. Record client sign-off (the gate)

```bash
./forge decision new client-signoff
# fill Context/Decision/Consequences, get the client's confirmation, then:
./forge decision accept client-signoff --by "<human name>"
python3 .agents/scripts/record_signoff.py
```

Every phase from `planning` onward is refused until this is recorded —
`update_run.py` and the pre-tool hook both enforce it.

## 6. Generate the workspace

Hand `harness/nestjs-react/SCAFFOLD_PROMPT.md` to Codex (via `/codex:rescue`
from Claude Code, or `codex exec`) to generate the nx workspace following the
conventions in `harness/nestjs-react/conventions/` and `constitution/`.

## 7. The feature loop

**At any point, in any phase, run `./forge next`** —
it prints where the project is and the exact next commands (the `/forge`
skill in Claude Code runs it for you and routes to the right tool). The steps
below are what it will walk you through.

For each feature (see `WORKFLOW.md` and `harness.yaml` for phase ownership):

```bash
python3 .agents/scripts/intake.py --issue ENG-123 --title "Build billing dashboard"
```

1. **Plan** — Claude Code plan mode following `.agents/prompts/planner.md`,
   delegating all codebase exploration to Codex read-only runs
   (`/codex:rescue` or `codex exec -s read-only`) — or, if you prefer planning
   in Codex, spawn the `planner-high` agent with the same prompt. Either way:
   record every new decision (`forge.py decision new <slug>`), then persist
   the approved plan:

```bash
./forge plan save --from <approved-plan-file>
```

2. **Decompose** — `docs-decomposer` with `.agents/prompts/decomposer.md`, then:

```bash
python3 .agents/scripts/record_decomposition_from_json.py --input /tmp/decomposition.json
python3 .agents/scripts/update_run.py --phase implementing --plan-status approved --decomposition-status recorded
```

3. **Implement** — delegate to Codex (`/codex:rescue --background`), one
   bounded task at a time.
4. **Test + verify**:

```bash
python3 .agents/scripts/record_test_from_json.py --kind automated --input /tmp/automated-test.json
python3 .agents/scripts/verify.py
```

5. **Review** — spawn `quality-reviewer`, `performance-reviewer`,
   `security-reviewer` (project-scoped agents under `.codex/agents/`); record:

```bash
python3 .agents/scripts/record_review_from_json.py --aspect quality --input /tmp/quality-review.json
python3 .agents/scripts/record_review_from_json.py --aspect performance --input /tmp/performance-review.json
python3 .agents/scripts/record_review_from_json.py --aspect security --input /tmp/security-review.json
```

   For security-sensitive, migration, or cross-domain tasks, escalate with the
   autoreview skill at PR-ready (see `harness.yaml`) — never both loops on one
   task.

6. **Functional check + PR-ready**:

```bash
python3 .agents/scripts/record_test_from_json.py --kind functional --input /tmp/functional-test.json
python3 .agents/scripts/pr_ready.py
```

`pr_ready.py` exits non-zero if any required artifact is missing. Merge stays
manual.

---

## Keeping your repo honest

CI runs these on every PR (and you can run them any time):

```bash
python3 .agents/scripts/check_dual_runtime.py   # reference-not-duplicate contract
python3 .agents/scripts/check_agents_hygiene.py # AGENTS.md size + links
python3 .agents/scripts/check_factory_scaffold.py
```

If codex-plugin-cc is unavailable, see `docs/degraded-mode.md` — same phase
prompts, same artifacts, direct `codex exec`.

## Upgrading a project to a newer harness

From the harness clone (clean target tree required):

```bash
./forge upgrade --target ../my-app
```

Harness-owned machinery (`.agents/`, adapters, `constitution/`, contracts) is
replaced; project-owned content (`harness.yaml`, `AGENTS.md`, plans, decisions,
context, prototype, `.factory/`) is never touched, and
`.agents/skills/proposed/` survives the swap. Review the diff, run the checks,
commit.
