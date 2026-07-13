# Getting Started with Symphony Forge

Symphony Forge is a dual-runtime harness plus doc-driven factory for building
agent-ready software. Claude Code coordinates; Codex executes. This page is
the one blessed path from empty directory to first feature PR.

**You drive it with sentences, not commands.** Every step below leads with
what you SAY to Claude Code (or Codex); the command underneath is what the
agent runs for you — the deterministic contract, and your fallback in
degraded mode. The only commands a human ever types personally are the
one-time clone and `decision accept` (confirming decisions is deliberately
human-only).

Lost at any point, in any phase? Say **"what's next?"** — the agent runs
`./forge next` and walks you through the exact next actions.

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

Say: **"Set up my machine for CAW projects."**

```bash
./forge doctor --fix
```

`--fix` auto-installs everything installable (Codex CLI via npm,
codex-plugin-cc and ponytail via the `claude plugin` CLI, gstack and
autoreview from their GitHub repos, mattpocock/skills and Anthropic's
frontend-design via the `skills` CLI).
Only logins (`codex login`) stay manual.
Re-run until it says `ready`.

## 3. Create your project

Say: **"Set up a new CAW project called my-app."** (the `caw-new-project`
skill installed by `./setup`)

```bash
./forge init --name my-app --target ../my-app
cd ../my-app
```

This scaffolds a complete, git-initialized repo: dual-runtime adapters
(`.claude/`, `.codex/`), shared agent assets (`.agents/`, including the
artifact schemas under `.agents/schemas/`), the vendored engineering
constitution, the phase manifest + skill allowlist (`harness.yaml`), doc
contracts, and an armed sign-off gate. It fails on a non-empty target.

> Do NOT create client projects with `gh repo create --template` — a template
> copy drags along the harness's own plans, run state, and history.

## 4. Discovery and prototype (phases 0a / 0b — lightweight on purpose)

Say: **"Let's run office hours on this idea."** (gstack `/office-hours`) and
fill `docs/product/DISCOVERY.md` and `docs/product/BRIEF.md` from it.
Prototype freely — no `.factory` ceremony before sign-off; the prototype is
preserved under `prototype/` afterwards as the forever UX reference.

Capture every client decision as you go — say: **"Record that as a
decision."**

```bash
./forge decision new <slug>
```

## 5. Record client sign-off (the gate)

Say: **"The client signed off."** The agent drafts the record and relays the
accept command — a HUMAN runs the accept:

```bash
./forge decision new client-signoff
./forge decision accept client-signoff --by "<human name>"   # human-typed
python3 .agents/scripts/record_signoff.py
```

Every phase from `planning` onward is refused until this is recorded.

## 6. Generate the workspace

Say: **"Scaffold the workspace."** The agent hands
`harness/nestjs-react/SCAFFOLD_PROMPT.md` to Codex to generate the nx
workspace per `harness/nestjs-react/conventions/` and `constitution/`.

## 7. Record the roadmap (the handoff backlog)

Say: **"Build the project roadmap."** The agent runs the project-level
decomposition (`docs-decomposer`, `.agents/prompts/decomposer.md`) against
the BRIEF and architecture docs, then records the ordered feature list:

```bash
./forge roadmap import --input /tmp/roadmap.json   # items in execution order
./forge roadmap list
```

`plans/roadmap.json` is the durable backlog: intake marks items active,
`pr_ready.py` marks them done with history links, and "what's next?" always
knows the next feature. Refine it by PR as planning teaches you more.

## 8. The feature loop

Start each feature with: **"Start the next task on the roadmap."**

```bash
python3 .agents/scripts/intake.py --issue ENG-123 --title "Build billing dashboard"
```

1. **Plan** — say: **"Plan this task."** Claude Code plan mode per
   `.agents/prompts/planner.md` (exploration delegated to Codex read-only;
   `planner-high` in Codex is the sanctioned alternate). New decisions get
   records; on approval say: **"Save the plan."**

```bash
./forge plan save --from <approved-plan-file>
```

2. **Decompose** — say: **"Decompose it."** (`docs-decomposer`; the recorded
   JSON must match `.agents/schemas/decomposition.json`, incl. the
   `user_facing` flag):

```bash
python3 .agents/scripts/record_decomposition_from_json.py --input /tmp/decomposition.json
python3 .agents/scripts/update_run.py --phase implementing --plan-status approved --decomposition-status recorded
```

3. **Implement** — say: **"Implement it."** (Codex,
   `/codex:rescue --background`, one bounded task at a time). The implementer
   writes and runs the tests and records the artifact itself:

```bash
python3 .agents/scripts/record_test_from_json.py --kind automated --input /tmp/automated-test.json
python3 .agents/scripts/verify.py
```

4. **Review** — say: **"Review it."** ONE autoreview run in Codex, three
   lenses (`.agents/prompts/reviewer.md`), three recorded artifacts:

```bash
python3 .agents/scripts/record_review_from_json.py --aspect quality --input /tmp/quality-review.json
python3 .agents/scripts/record_review_from_json.py --aspect performance --input /tmp/performance-review.json
python3 .agents/scripts/record_review_from_json.py --aspect security --input /tmp/security-review.json
```

5. **Functional check** — only when the decomposition says
   `user_facing: true`; then: **"Is this PR ready?"**

```bash
python3 .agents/scripts/record_test_from_json.py --kind functional --input /tmp/functional-test.json
python3 .agents/scripts/pr_ready.py
```

`pr_ready.py` exits non-zero if any required artifact is missing, unstamped,
or stale. Merge stays manual.

---

## Continuously: the context inbox

Client emails, meeting transcripts, voice-note summaries, stray docs — drop
them in `docs/context/` the moment you get them. Dumping is free; tracking is
automatic. Then say: **"Process the context dump."**

```bash
./forge context scan                 # register files in docs/context/ledger.json
# agent harvests per .agents/prompts/harvester.md:
#   pending file -> proposed decision records + DISCOVERY/BRIEF/architecture edits
./forge context mark <file> --harvested --outputs <paths>   # or --ignored --notes "why"
./forge context list --pending
```

**You will not miss pending context — four surfaces make sure:**
1. every agent session opens with the unharvested count (SessionStart hook)
2. `./forge next` puts "harvest first" as step 1 in any phase
3. the daily `gardener` workflow opens a GitHub issue while anything is
   pending, and closes it at zero
4. `./forge plan save` **refuses** while context is pending — you cannot
   approve a plan over an unread client email

Decisions proposed by a harvest still need a HUMAN accept
(`./forge decision accept <slug> --by "Name"`).

## Keeping your repo honest

Recorders refuse any artifact that does not match its schema in
`.agents/schemas/` — wrong shape, wrong types, or a `generated_by` outside
the `harness.yaml` allowlist. Adopting a new tool is a harness PR, never a
local choice (see WORKFLOW.md "Determinism Contract").

CI runs these on every PR (and you can run them any time):

```bash
python3 .agents/scripts/check_dual_runtime.py   # reference-not-duplicate + schema/allowlist parity
python3 .agents/scripts/check_agents_hygiene.py # AGENTS.md size + links
python3 .agents/scripts/check_factory_scaffold.py
```

If codex-plugin-cc is unavailable, see `docs/degraded-mode.md` — same phase
prompts, same artifacts, direct `codex exec`.

## Migrating an existing repo into the harness

Already built a prototype (or an early project) with agents, outside the
harness? Say: **"Migrate this repo into the harness."** (the
`caw-migrate-project` skill installed by `./setup`)

The deterministic core is `forge adopt`, run from the harness clone against a
CLEAN target tree:

```bash
./forge adopt --target ../legacy-repo --name my-app
```

It vendors the machinery, preserves any pre-existing `AGENTS.md`/`CLAUDE.md`
into `docs/context/migrated-*` (the harvester picks them up), creates
project-owned files only where missing, and never deletes existing work —
every overwrite is a reviewable git diff. The skill then walks the judgment
part: sorting code into `prototype/`, dumping notes into `docs/context/`,
harvesting DISCOVERY/BRIEF and decision records, formalizing a historical
sign-off, and handing off to `./forge next`. Repos that already carry the
harness are routed to `forge upgrade` instead.

## Upgrading a project to a newer harness

Say: **"Upgrade this repo to the latest harness."** From the harness clone
(clean target tree required):

```bash
./forge upgrade --target ../my-app
```

Harness-owned machinery (`.agents/` incl. schemas, adapters, `constitution/`,
contracts) is replaced; project-owned content (`harness.yaml`, `AGENTS.md`,
plans incl. the roadmap, decisions, context, prototype, `.factory/`) is never
touched, and `.agents/skills/proposed/` survives the swap. Review the diff,
run the checks, commit.
