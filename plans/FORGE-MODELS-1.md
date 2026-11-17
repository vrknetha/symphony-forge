# Short model names pick the newest model at each run

2 parts · Risks: none one-way; four accepted limits · New moving parts: none

## What changes for you

- `forge.toml` can name a model with a short name: `sol`, `astra`, `terra` or `luna` for Codex, and `sonnet`, `opus` or `haiku` for Claude. (Source: the owner's request, 18 Nov 2026)
- With a short name, each build, cold read and review uses the newest model of that name that the installed tool offers. Forge checks this when each one starts, not when Forge upgrades. When Codex adds a newer Sol, the next build uses it, with no new Forge release and no edit. (Source: the owner's request, 18 Nov 2026)
- A full model name, such as `gpt-6.1-terra`, stays exact: Forge uses that model and nothing else. (Source: the owner's request, 18 Nov 2026)
- Each round's line and its record name the exact model that ran, such as `gpt-6.2-sol`, not only the short name. (Source: the owner's request, 18 Nov 2026)
- If Codex offers no model of a short name, the round stops before it starts, with one line that lists the models Codex offers. (Source: the owner's request, 18 Nov 2026)
- What each repo gets. A new repo's `forge.toml` starts with short names, so it always gets the newest models. Reviews and cold reads on Codex stay on Terra at max effort: `terra` means `gpt-6.1-terra` today. An existing repo keeps its model names on upgrade; Forge changes nothing in its `forge.toml`. Its owner can change any name to a short name at any time. (Source: the owner's request, 18 Nov 2026)
- Cost. No model call is added. A Codex short name adds one quick local call to Codex's model list when a round starts (about a tenth of a second). A newer model can cost more or less than the one it replaces. (Needed by: the short names above)

Design: none. The board and the pull request look the same; their model names are now the exact ones.

## Why

Forge's defaults and each client's `forge.toml` name fixed model versions, such as `gpt-6.1-sol`. When Codex or Claude adds a newer model, Forge needs a new release to change its defaults, and each client repo needs a hand edit. Until then, every repo keeps building on the older model. Today Codex already offers `gpt-6.2-sol`, and new repos still start on `gpt-6.1-sol`.

## Done when

1. **With a short name in `forge.toml`, each build, cold read and review uses the newest model of that name that the installed tool offers, checked when it starts, and a full name uses exactly that model.**
2. **Each round's line and record name the exact model that ran, and a Codex short name that the installed Codex does not offer stops the round before it starts, with one line that lists the models Codex offers.**
3. **A new repo's `forge.toml` starts with short names, with reviews and cold reads on Terra at max effort, and an existing repo's model names do not change on upgrade.**

## Risks

Risks: none one-way. Each part reverts with its pull request. No saved record changes. No existing repo's `forge.toml` changes.

Accepted limits, in plain words:
- Claude decides what `sonnet`, `opus` and `haiku` mean. On some cloud providers they mean an earlier model. Forge does not check Claude's short names; Claude always accepts them.
- When a Claude session runs a round as its own subagent, Forge cannot see the model that the subagent used. That round's record keeps the short name. Rounds that Forge starts itself, and all reviews, name the exact model.
- Files that Forge writes for Codex's own use cannot hold a short name, because Codex refuses short names. When `forge.toml` uses one, those files leave the model out. The round itself still names the exact model when it starts. Only the helpers that a Codex session's subagent starts on its own use that session's model.
- Before a round starts, the board shows the name from `forge.toml`. The exact name shows when the round runs.

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

Checked in this worktree on 18 Nov 2026 (base `856e51ad4`, Forge v1.2.41). The builder checks each name again before it starts.

### Done-when details

1. Short names resolve when each run starts; full names stay exact.
   - **How "newest" is chosen.** A Codex short name `<name>` matches each slug `gpt-<version>-<name>` that `codex debug models` lists with `"visibility": "list"`. `<version>` is dot-separated whole numbers (`6`, `6.1`, `6.2`). The newest is the highest version, compared number by number. Hidden models (`"visibility": "hide"`) never count. Read only `models[].slug` and `models[].visibility`, and ignore every other field.
   - **Why the version, not `priority`.** Codex lists `priority` for its picker order. It is lower for newer models today, but that is not a promise. The version in the slug is.
   - **Today (Codex CLI 0.169.0 on this machine):** `sol` → `gpt-6.2-sol`, `astra` → `gpt-6.2-astra`, `terra` → `gpt-6.1-terra`, `luna` → `gpt-6-luna`. `codex debug models` took 0.1 s and runs no model.
   - **Codex refuses short names itself.** Checked: `codex exec -m luna` fails with "The 'luna' model is not supported when using Codex with a ChatGPT account." So Forge must resolve every Codex short name before Codex sees it.
   - **Claude accepts its short names itself.** The Claude Code docs (code.claude.com, model configuration and subagents pages) say `sonnet`, `opus` and `haiku` "resolve to the newest version on the Anthropic API". `--model`, the Agent SDK's `model` option and a subagent file's `model:` field all take them. Checked: `claude -p --model haiku --output-format stream-json --verbose` (Claude Code 2.1.325) reports `claude-haiku-5-5` in the `system`/`init` event's `model`, in each assistant message's `model`, and as the only key of the result's `modelUsage`. So Forge passes Claude short names through unchanged and records what Claude reports.
   - **When.** Once per Forge process, at the first Codex short name a run needs (`functools.cache`). Each `forge work`, `forge read` and `forge close` is a new process, so each run reads the list again. A repo whose names are all full names never calls `codex debug models`.
   - **Which binary.** The same one the review launcher and doctor use: `shutil.which(os.environ.get("CODEX_BIN") or "codex")` (`src/forge/review.py:1174`, `src/forge/doctor.py:353`). The builder checks that the Codex SDK's `Codex()` in `src/forge/codex_turn.py:144` starts the same binary; if it does not, say so in the handoff.
   - Test: `tests/test_short_model_names.py::test_1_a_codex_short_name_runs_the_newest_listed_model_at_each_run`, `STORY = "FORGE-MODELS-1"`, parametrized `step` = `work`, `read`, `close`. Use `_codex_repo` from `tests/test_codex_worker.py` (new repo), with the stub's model list set by a new `STUB_CODEX_MODELS` variable (see Decisions). The list holds `gpt-6.1-sol`, `gpt-6.2-sol`, `gpt-6.3-sol` hidden, `gpt-6.2-astra`, `gpt-5.6-terra`, `gpt-6.1-terra`, and one field Forge never heard of.
     - `work`: `[models.build.codex]` `model = "sol"`. The stub's `thread/start` config has `"model": "gpt-6.2-sol"`, and stdout has `Building BOARD/PAGE with Codex (gpt-6.2-sol, low`. Then list `gpt-6.3-sol` as visible and run `forge work BOARD/PAGE --note "again"`: the second `thread/start` has `gpt-6.3-sol`. Then set `model = "gpt-6.1-sol"`: the next `thread/start` has `gpt-6.1-sol`, and the stub logs no `debug models` call for that run.
     - `read`: `[models.grill.codex]` `model = "terra"`, `effort = "max"`, on a story plan read with the Codex reader. `thread/start` has `gpt-6.1-terra`, and the plan's read notes name `codex (gpt-6.1-terra)`.
     - `close`: `[models.review.codex]` `model = "terra"`. The Autoreview stub's arguments hold `--model codex=gpt-6.1-terra`.

2. Exact model in each round line and record; a missing Codex model stops the round.
   - **Codex.** Once the name is resolved before the run, the existing lines and records carry it: the `Building ...` line (`src/forge/worker.py:226`), the agent slot (`worker.py:247-248`), the run record (`codex.turn`, `src/forge/codex.py:603-606`), the native hand-out (`src/forge/native.py:145-153`) and the read offer (`native.offer`, `native.py:122`). The kit turn already reports the model Codex chose, from `thread/start` (`src/forge/codex_turn.py:236-240`, recorded at `codex.py:670-674`).
   - **Claude, kit rounds.** Already exact in the record: `repo.claude_output` (`src/forge/repo.py:545-548`) records the `init` event's `model` for builds and for Claude cold reads (`src/forge/story.py:994`). New: when that model differs from the requested name, print one line `Claude runs <exact> for <short>.` to the terminal and the work log, so the round line names it.
   - **Claude reviews.** Autoreview prints only the name it was given (`model: <name>`, read at `src/forge/autoreview.py:76-80`). New: `autoreview.spent` (`autoreview.py:19-45`) also returns `model`: the `modelUsage` key with the most `outputTokens` in Claude's `result` event, which Forge's launcher already saves. `review.py:993` (`ran.update(selected, **autoreview.spent(...))`) then records it over the given name.
   - **Cold-read notes.** `story.py:403` writes `reader: <tool> (<result["model"]>)`, which is the configured name today (`story.py:308`). New: use the model the run recorded when it has one, else the resolved name.
   - **The stop.** A new refusal in the new module: `("Codex here has no {name} model. It offers {offered}.", "set that model in forge.toml's [models] to one of these, or update Codex, then run the command again")`. `{offered}` is the visible slugs in Codex's order, joined with ", ". If `codex debug models` fails or its output is not the expected JSON, `{offered}` is `no models it could list ({last line of its output})`. The refusal comes before any agent slot, lock, thread or run record.
   - Test: `tests/test_short_model_names.py::test_2_a_claude_short_name_reaches_claude_and_the_round_names_the_exact_model`. Claude workers on a new repo with `[models.build.claude]` `model = "sonnet"`, the stub SDK (`tests/stubs/claude_agent_sdk.py`) answering `sonnet` with `claude-sonnet-5-5` in its `init` event. The SDK's `model` option is `sonnet`; stdout has `Claude runs claude-sonnet-5-5 for sonnet.`; the worker run's record names `claude-sonnet-5-5`, read as `tests/test_effort_defaults.py:38-42` reads it. Then close with `[models.review.claude]` `model = "sonnet"`: Autoreview gets `--model claude=sonnet`, and the review run's record names `claude-sonnet-5-5`. To get there, the Autoreview stub runs the `--claude-bin` launcher that Forge gives it once, with a stub `claude` that prints one `result` line whose `modelUsage` has `claude-sonnet-5-5`.
   - Test: `tests/test_short_model_names.py::test_3_a_codex_short_name_codex_lacks_stops_the_round_listing_its_models`. Codex workers, `[models.build.codex]` `model = "luna"`, with a list that has `gpt-6-luna` only as hidden. `forge work` exits non-zero; stderr is exactly `Codex here has no luna model. It offers <the visible slugs>.` and its `Next:` line. The stub logs no `thread/start`, and no run start is recorded.

3. New repos start with short names; existing repos keep theirs.
   - **New repos.** `init.MODELS` (`src/forge/init.py:77-148`) changes only model names, never efforts: `gpt-6.1-sol` → `sol`, `gpt-6.1-terra` → `terra`, `gpt-6-luna` → `luna`, `claude-sonnet-5-5` → `sonnet`, `claude-haiku-5-5` → `haiku`. Reviews, light reviews and cold reads on Codex stay `terra` at `max`.
   - **Files Forge writes for Codex.** `forge sync` writes `.codex/agents/<role>.toml` from `roles.ships` (`src/forge/roles.py:111-132`) and the helper default `default_subagent_model` in `.codex/config.toml` from `roles.subagent_defaults` (`roles.py:102-108`, written at `src/forge/sync.py:268-269` and `:302-309`). Codex refuses short names there too. When the value is a Codex short name, leave out that `model` line or the `default_subagent_model` key, and keep the effort. Claude's `.claude/agents/<role>.md` keep the short name; Claude accepts it.
   - **Built-in defaults stay full names.** `repo.WORKER_DEFAULTS`, `DESIGN_DEFAULTS`, `CLAUDE_GRILL_DEFAULT` and `SUBAGENT_DEFAULT` (`src/forge/repo.py:625-631`) apply to existing repos with a missing entry. Changing them would change those repos' models without an edit by their owner.
   - **Existing repos.** No change on upgrade: upgrade and sync already keep model entries (skill.md: "Existing model and effort entries stay unchanged after upgrade and sync"). No upgrade-test change, and no earlier-adopted case (the review rules: an ordinary rule is tested on a new repo only).
   - Test: `tests/test_short_model_names.py::test_4_a_new_repo_starts_with_short_names_and_codex_files_hold_none`. `forge init` a new client (`_fresh_client` from `tests/test_setup.py`). Its `[models]` table equals the expected table with the short names above and today's efforts. No `.codex/agents/*.toml` has a `model` line with a short name. `.codex/config.toml` has no `default_subagent_model`. `.claude/agents/worker.md` has `model: "sonnet"`.
   - Existing tests that read init's names change only those expected names (`sol` and so on for the `forge.toml` text; `sonnet` and `haiku` for what Claude is sent). The stub's default list (see Decisions) keeps every resolved Codex name as it is today, so assertions on what Codex is sent stay. Candidates, from a search for init plus a default name: `tests/test_effort_defaults.py`, `test_design_models.py`, `test_read_only_model_selection.py`, `test_codex_review_defaults.py`, `test_claude_implementation_defaults.py`, `test_claude_subagent_defaults.py`, `test_claude_subagents.py`, `test_fix_first_codex_round_luna_helpers.py`, `test_fix_gpt_6_1_sol_is_out_and_about_40_cheaper.py`, `test_personal_worker_choice.py`, `test_reviews_use_configured_models.py`, `test_effort_ladder.py`. Run them all; change only the ones that fail on a name.

### What exists (evidence)

- **Who reads models.** `repo.models` (`src/forge/repo.py:797-809`), `worker_models` (`:818-820`), `design_models` (`:889-891`), `subagent_budget` (`:823-827`). A single (not per-family) entry counts for Codex only when its model `startswith("gpt")` (`:809`), so `sol` would count as Claude's. `roles._family` (`src/forge/roles.py:71-72`) already treats any name that is not Claude's as Codex's, so `sol` is right there. `_models_problem` (`repo.py:894-922`) checks no model name.
- **Where a model reaches a tool.**
  - Codex kit build, fix, lite, design and cold read: `codex.turn` builds `request["config"]` from `settings(config, kind)` and the design entry (`src/forge/codex.py:569-588`), mapped by `OVERRIDES` (`:60-62`), so both `model` and `agents.default_subagent_model` go to Codex here.
  - Codex review: `review.py:969-974` adds `--model codex=<model>` for Autoreview, which passes it to Codex unchanged (Autoreview checks no names).
  - Native rounds: `native.hand_out` prints `Start it on <model> at <effort> effort` (`native.py:153`); `native.offer` prints the read's models (`native.py:122`).
  - Claude: `worker.ready` (`src/forge/worker.py:466-472`) and the design path (`:341`) give `--model`; `worker._run` and `story._sdk_read` send it to the SDK (`worker.py:818-831`, `story.py:965-974`); `src/forge/claude_turn.py:33-34` passes it to `ClaudeAgentOptions`. The SDK's helper agents get `subagent_budget` (`worker.py:333`, `:826-828`).
  - The worker's fallback from Claude to Codex design (`worker.py:354-358`) prints the Codex design model.
  - The intake explorer (`src/forge/intake.py:45`) uses the explore entry, through the same paths.
- **Board.** A running round shows the recorded model (`src/forge/board.py:456-461`); an idle item shows the configured one (`board.py:435-448`). No change.
- **Line ceilings** (`tests/test_rules.py::test_5_forge_stays_small`, 1,200 lines): `codex.py` 1,200, `repo.py` 1,199, `review.py` 1,199, `story.py` 1,193. `codex.py` must not grow at all. The new code goes in a new module.
- **Test stubs.** `_codex_repo` installs `tests/stubs/codex-app-server` and sets `CODEX_BIN` to it (`tests/test_codex_worker.py:113-141`). `tests/test_close.py:273-274` installs its own `CODEX_STUB` as `codex`. 34 test files set `CODEX_BIN`; only runs with a Codex short name call `debug models`, so most stubs need nothing.

### Options weighed

1. **Resolve at upgrade or sync and write the full name into `forge.toml`.** Rejected by the owner: the model must be the newest at each run, and `forge.toml` must not change on its own.
2. **Resolve inside the Codex kit through the app-server's `model/list`** (already called at `codex_turn.py:221-232`). Rejected: reviews (Autoreview) and native rounds never start the app-server, so they would need a second way.
3. **Resolve inside `repo.models`.** Rejected: the board, `forge next` and `forge sync` call it too. They would call Codex, and a missing model would stop the board.
4. **One small resolver called where a run starts (chosen).** One list call per process, only for Codex short names, at the four places a run takes its model.
5. **Map Claude short names in Forge too.** Rejected: Claude Code already maps them, and the right model depends on the provider, which only Claude Code knows.

Score (F x H >= 2 x C): F 2 (a newer model comes every few weeks, and each needs a release plus an edit in every repo), H 2 (repos keep building on an older model: a slower or worse step), C 2 (about 100 product lines, no model call, no user step): 4 >= 4, kept.

### Decisions

- **New module `src/forge/model_names.py`** (about 40 lines): `CODEX = ("sol", "astra", "terra", "luna")`, `CLAUDE = ("sonnet", "opus", "haiku")`, `REFUSALS` with the stop above, a cached `_listed()` that runs `<codex> debug models` (timeout 30 s) and returns the visible slugs in Codex's order, and `exact(entry: dict) -> dict`, which returns the entry with `model` and `subagents` changed from a Codex short name to the newest slug, and every other value unchanged. Merge its `REFUSALS` the way `close.py:75` merges `review_skip.REFUSALS`, if a refusal check needs it.
- **Family rule.** `repo.models` line 809: a model is Codex's when it starts with `gpt` or is in `model_names.CODEX`. Change that one line; import inside the function if a top import would pass 1,200 lines. The guide's sentence "a gpt model is Codex's, any other Claude's" changes to match.
- **Call sites** (each one line, or a change to an existing line):
  - `worker.work`: right after `chosen` is picked for a Codex round (`worker.py:214-220`), and at the design fallback (`worker.py:354`), `chosen = model_names.exact(chosen)`. This covers the round line, the agent slot, the native hand-out and its record.
  - `codex.turn` (`codex.py:571-575`): pass the kind's entry and the design entry through `model_names.exact` before `OVERRIDES`, inside existing lines so `codex.py` stays at 1,200.
  - `review.py:969-972`: `model = model_names.exact(model)` for the Codex engine, after the light-review merge.
  - `story.read`: take `repo.models(config, "grill", reader)` once (it is called four times at `story.py:308-332`), pass it through `exact` when the reader is Codex, and use that one value at each place.
- **Claude line.** In `repo.claude_output`, at the `init` event: when `event["model"]` differs from `ran["model"]`, print `Claude runs <exact> for <requested>.` before `ran.update`. The work log gets the line the same way the other printed lines do.
- **Claude review model.** `autoreview.spent` adds `model` from the `modelUsage` key with the most `outputTokens`, only when a `result` event has `modelUsage`. Codex review runs keep the name Forge gave, which is already exact.
- **Stub.** `tests/stubs/codex-app-server` answers `debug models` with `{"models": [...]}` from `STUB_CODEX_MODELS` (a JSON list of `[slug, visibility]` pairs), else a default list that resolves each short name to today's init name: `gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-luna`, `gpt-6-astra`, all visible. Every reply adds one unknown field, as the stub's other replies do. It logs each `debug models` call.
- **Guide.** Part RESOLVE adds to the `[models]` paragraph in `src/forge/templates/skill.md` (now at `:1866-1872`): the short names and what each means; "the newest listed model of that name, checked when each build, cold read and review starts; a full name stays exact"; the stop line and what to do; and that native Claude subagent rounds keep the short name in their record. Part DEFAULTS changes the default names in the same section (`:1870-1914`) and in `docs/guide.md:406-458`. Refresh `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md` with this checkout's `forge sync`, or edit the same lines by hand; commit only those lines' changes. No `brief.md` change: workers do not choose models.
- **Not added.** No check of model names in `forge doctor` or at config load (the round stops instead, as the owner asked); no model-list cache on disk; no change to Claude short names; no migration of existing repos; no change to the built-in defaults.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| RESOLVE | Short names resolve at each run | The new module and its stop, the family rule, the four call sites, the Claude round line, the Claude review model, the read notes' model, the stubs' model lists, the guide's short-name paragraph | 1, 2 | `src/forge/model_names.py` (new), `src/forge/repo.py` (`models` and `claude_output` only), `src/forge/worker.py`, `src/forge/codex.py` (`turn` only), `src/forge/review.py` (the model arguments only), `src/forge/story.py` (`read` and `read_result` only), `src/forge/autoreview.py`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `tests/stubs/codex-app-server`, `tests/stubs/autoreview`, `tests/stubs/claude_agent_sdk.py`, `tests/test_short_model_names.py` (new) | `tests/test_short_model_names.py::test_1_a_codex_short_name_runs_the_newest_listed_model_at_each_run`, `::test_2_a_claude_short_name_reaches_claude_and_the_round_names_the_exact_model`, `::test_3_a_codex_short_name_codex_lacks_stops_the_round_listing_its_models`; existing, stay green: `tests/test_models_per_family.py`, `tests/test_reviews_use_configured_models.py`, `tests/test_rules.py::test_5_forge_stays_small` | | no | |
| DEFAULTS | New repos start with short names | Init's short names, sync leaving short names out of Codex's files, the guide's default names, the existing tests' expected names | 3 | `src/forge/init.py` (`MODELS` only), `src/forge/roles.py`, `src/forge/sync.py` (the helper default only), `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `docs/guide.md`, `tests/test_short_model_names.py`, the existing tests listed under item 3 | `tests/test_short_model_names.py::test_4_a_new_repo_starts_with_short_names_and_codex_files_hold_none`; changed: only the expected names in the tests listed under item 3 that fail; existing, stay green: `tests/test_read_only_model_selection.py`, `tests/test_upgrade_to_installed_release.py` | RESOLVE | no | |

New moving parts: none

## Notes

- **Principle 6.** Adds about 100 product lines and no command, setting or file kind. It removes a Forge release and a hand edit in every client repo each time a newer model comes out.
- **Model cost.** No model call is added. Today `sol` means `gpt-6.2-sol`, so new repos build on `gpt-6.2-sol`, not `gpt-6.1-sol`. Not verified: the price of `gpt-6.2-sol` against `gpt-6.1-sol`. `astra` is allowed as a name; no default uses it.
- **Before each builder round ends**, run the two cheap checks from AGENTS.md (`test_4_one_test_per_rule`, `test_5_forge_stays_small`).
- **Owner questions (recommended answer first).**
  1. Files Forge writes for Codex's own use cannot hold a short name. Leave the model out there (recommended: nothing changes when Codex adds a model, and each round names its exact model anyway), or write the newest full name at each sync (the committed files then change whenever Codex adds a model, and two people with different Codex versions get different files).
  2. A Claude session subagent round records the short name, not the exact model (recommended: accept it; Forge cannot see the subagent's model, and Claude picks its newest), or ask the session to hand back the model with the round's result (one more step for each round, and the session may not know it).
  3. Forge's built-in defaults, used when `forge.toml` has no entry, stay full names (recommended: changing them would change existing repos' models without their owner's edit), or become short names too.
- **Not verified.** That the Codex SDK starts the same `codex` binary as `CODEX_BIN` (the builder checks); what Claude's short names mean on providers other than the Anthropic API (Claude's own docs say they can mean an earlier model).
