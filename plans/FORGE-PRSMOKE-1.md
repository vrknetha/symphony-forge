# Run fewer tests on Forge pull requests

1 part · Risks: none one-way; three accepted limits · New moving parts: none

## What changes for you

- A repo can set `test_select = "small"` in forge.toml. With it, the pull request check and close run only three kinds of test: the test files the change adds or edits, the tests its Proof list names (the Proof list is the list of tests that prove each Done-when item), and a short fixed list of basic tests. This holds even for a change to core code. Today a one-line edit to `src/forge/close.py` picks 955 of the 960 test files, because every Forge test runs the real `forge` command. (Source: the owner's choice, 27 Nov 2026, option A)
- The list of basic tests is the file `.forge/always-tests.txt`, which Forge already reads. A person keeps it by hand. No new file is added. This story adds a few end-to-end tests of Forge's main commands to it, and the builder keeps the list short. (Source: the planner's choice for you to confirm)
- In `small` mode the pull request check uses one test group, not six. The full suite still runs every test, and the setting does not change it. In a repo whose tests run on GitHub (`test_place = "ci"`), the full suite runs once a night on main and by hand before a release. A release tag is refused until the latest commit on main has a green full run. This is how Forge works today. (Source: the owner's choice, 27 Nov 2026)
- If the nightly run fails, the board and `forge next` show it under "Needs you" with a link to the run. The next-step line gives the exact command that opens the fix, and the agent runs it. Forge does not open the fix without an agent. Merges of other tasks wait until the fix merges; fixes themselves still merge. This also works today.
- GitHub cost, from your numbers: one full run is about 6 machines for about 30 minutes, which is about 180 machine-minutes. Today every pull request with a core edit costs that. After this story, a pull request costs one machine for a short run (not measured yet; the builder measures one real run). The nightly run costs about 180 machine-minutes a day. A run by hand before a release costs the same, and only when main moved after the last nightly run. So the repo saves minutes on any day with two or more such pull requests.
- What each repo gets: a new repo and an existing repo get no change. The default stays as today: Forge picks every test that the changed files can reach. A repo uses `small` only after its owner or agent writes it in forge.toml through a settings fix. The guide that every repo gets tells the agent what the value does and how to choose it. No saved record changes.
- This repo sets `test_select = "small"` after this story merges and a release that has it is installed, in one settings fix. The pinned Forge (`v1.2.50`) refuses an unknown setting until then. This repo stays on `test_place = "ci"` for the nightly run on GitHub. (Source: the owner's request, 27 Nov 2026; staying on `ci` is the planner's reading for you to confirm)

Design: none (no screen changes)

## Why

Every Forge test runs the real `forge` command, so the picker that chooses related tests finds a link from core code to almost every test. A small edit to `close.py` selects 955 of 960 test files. That takes about 2.5 hours on a laptop, or about 30 minutes on 6 GitHub machines, for each pull request. On 27 Nov 2026 you chose option A: pull requests run a small set, and the full suite runs once a night and before a release. Option B, a precise picker based on code coverage (story FORGE-FUNCSEL-1), comes after this story.

## Done when

1. **In a repo with `test_select = "small"`, close on this machine and the pull request check on GitHub run only the test files the change adds or edits, the tests its Proof list names, and the repo's list of basic tests, each once, even for a change to core code; the pull request check uses one test group.**
2. **The setting does not change the full suite: in a repo whose tests run on GitHub it runs every test once a night on main and by hand before a release, a release tag is refused until the latest commit on main has a green full run, and a failed run shows under Needs you with its link and the command that opens the fix.**
3. **A repo that does not set `test_select` picks tests and runs its pull request check exactly as today; forge.toml accepts `related` and `small` and refuses any other value; the guide tells the agent when and how to choose `small`.**

## Risks

Risks: none one-way. The part reverts with its pull request.

Accepted limits:
- Main can break between nightly runs. It broke 4 times in mid-November 2026, when pull request tests were thin. In `small` mode the nightly failure shows under Needs you the next morning, other tasks stop merging until the fix merges, and a release waits for a green full run. So a broken main lasts about one day.
- A pull request no longer finds a break in a test far from its change. The nightly run finds it, and the fix is a separate item. How often this happens is not known; the repo can go back to `related` with one settings fix.
- In `small` mode a change to a shared test input (`conftest.py`, `pyproject.toml`, a lock file) no longer selects every test. The nightly run covers it. A repo whose test command has a fixed shard count keeps all its groups in the pull request check.

## For the builders

Source: the owner's choice of 27 Nov 2026 (option A of "A now, then B"). Story tests use
`STORY = "FORGE-PRSMOKE-1"` and one test function per Done-when number: `test_1` to `test_3`.

### Done-when details

1. How the picker works today: `pytest_tests` (`src/forge/fasttest.py` line 813) calls `related(base)` (line 395), which returns the picked files, all test files, whether shared inputs changed, and the sources no test names. For a non-worker run it also reads the Proof list names, `proof.entries(top, item, "HEAD", base)`, kept in `named` (lines 842 to 849), and it adds `always_tests` (line 486: forge.toml's `always_test` plus `.forge/always-tests.txt` through `docskip.required_tests`). A worker run already has a narrow branch for a broad selection (lines 852 to 875): only the Tests column or the touched test files, plus `always`, with `shared_changed = False`. Small mode reuses that branch, so it adds almost no code.
   Change: read `test_select` from the forge.toml that line 836 already reads (one read, no second one). Extend the condition at line 852 to `small or worker and len(picked) * 3 > len(tests)`. In the small, non-worker case do not replace `named`: keep the Proof list names from line 848 and set `picked` to the changed and untracked test files (the `else` at lines 871 to 874); set `shared_changed = False`. Print one line in place of "Broad selection": "Small selection (test_select = small): changed tests, Proof list tests and the basic tests run. The nightly full run covers the rest." The existing dedupe (`dict.fromkeys`, and `listed` at line 882) makes each test run once.
   `repo.py` (1,185 lines; at most 3 added): add `"test_select": str` to `KEYS` (line 566) and `"test_select": ("related", "small")` to `CHOICES` (line 582). Add no `DEFAULTS` entry; read it with `cfg.get("test_select", "related")`. `repo.py` refuses an unknown key (line 912), which is also why the pinned release cannot read the setting early.
   `templates/review-tests.py` (319 lines; at most 6 added): inside the existing `try`, after the `if merged:` block (line 285), read forge.toml and, when `cfg.get("test_select") == "small"`, set `one_group = True`. Nothing else in the workflow changes: the `tests` job already reads the `one-group` output (`.github/workflows/forge.yml` lines 56 to 65). `forge sync` regenerates `.forge/review-tests.py` from the template (it adds the docs-only rule block); commit that copy in this part. A repo with a fixed shard count already forces `one-group` to `'false'` in `prcheck.py` (the `template.replace` at line 416); leave it.
   `.forge/always-tests.txt` today has 7 entries. Add 3 to 5 existing end-to-end tests of Forge's main commands (for example one each from `tests/test_close.py`, `tests/test_task.py`, `tests/test_merge_command.py`, `tests/test_next.py`, and an init test), chosen so the list runs in about 3 minutes on one machine. Measure it and say the time in the pull request. Docs-only pull requests also run this list through the single group, so each entry must be fast.
   Tests (new `tests/test_small_pull_request_tests.py`, a new repo with tiny real tests, as in `tests/test_close_runs_only_related_tests.py`, with `machine_runners`, `env` and the pytest receipt; GitHub stubbed): `test_1_...` builds a repo with `test_select = "small"`, about 12 test files that all import one core module, one test file in `.forge/always-tests.txt`, and a Proof list that names another. The change edits the core module and adds one new test file. `forge test --change` (and `forge close` with `test_place = "local"`) run exactly those three files, each once, and none of the other nine. The generated `.forge/review-tests.py`, run with `BASE_SHA`, `HEAD_SHA`, `DOCS_ONLY_EXCLUDES` and `GITHUB_OUTPUT` set as in `tests/test_docs_only_test_checks.py`, writes `one-group=true`. A change that edits a root `conftest.py` selects the same three files and not every test.
2. Nothing in the code changes for this item, so it is proven by tests that already exist, plus one new case. `fullrun.run` (`src/forge/fullrun.py` line 75) runs the repo's whole `test` command through `review.test_run(..., always=True)` and never calls `review.close_test`, so the setting cannot narrow it. `prcheck.py` (`full_run`, line 306) builds the nightly `full-suite` job (`schedule` at 03:00 UTC and `workflow_dispatch`) for `ci`. `githooks.pre_push` (line 195) calls `fullrun.green` before a release tag. `board_facts.failed_runs` and `nextstep._failed_schedules` show a failed run as "Needs you" with the `forge fix start` line. `merge.red` holds task merges while the full run is red.
   Existing tests the Proof list names for this item: `tests/test_testplace_fullrun.py::test_3_full_run_is_nightly_and_daily`, `tests/test_testplace_fullrun.py::test_4_failed_full_run_opens_a_fix`, `tests/test_testplace_fullrun.py::test_5_release_and_signoff_wait_for_a_green_full_run`, `tests/test_failed_full_run_needs_you.py::test_2_next_marks_only_the_full_test_run`, `tests/test_main_has_only_nightly_tests.py::test_1_sync_keeps_automatic_main_tests_only_in_the_nightly_run`. Do not copy them.
   New case, same file as item 1: `test_2_...` uses the repo of `test_1` with `test_place = "ci"` and `test_select = "small"`. `forge sync` writes a workflow whose `full-suite` job still has `schedule` and `workflow_dispatch` and runs `forge test --full`, and whose `tests` job runs `forge test --change`. `forge test --full` on the same repo runs all 12 test files (the receipt shows every file), with the status post stubbed as in `test_testplace_fullrun.py` `test_4_...`.
3. Tests, same file. `test_3_...`: the same repo without `test_select` runs all 12 test files for the same change, and `review-tests.py` writes `one-group=false`. `forge doctor` accepts `test_select = "related"` and `"small"`, and refuses `"sometimes"` with "test_select must be one of related, small". No new upgrade case: no record changes, so `tests/test_upgrade_to_installed_release.py` stays as it is, and the default is tested on a new repo only. Guide text: `templates/skill.md` gets a short paragraph beside the `test_place` text (lines 378 and 1757) and the `fast_test` / `always_test` text (line 2462 onwards): what `small` runs, that the full suite is unchanged, that the agent sets it only through a settings fix that the owner agrees to, and that only pytest repos are affected. `templates/brief.md` gets one sentence beside the related-test paragraph (line 358): with `test_select = "small"`, bare `forge test` and close run the same small set. The two synced skill copies (`.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`) are regenerated by `forge sync`.

## Tasks

<!-- One row per task. Covers: the Done-when numbers it delivers, at most three. Scope: the paths
it may change. Before writing each Scope, search the code for the files the task needs. The plan
check refuses two tasks whose Scope paths have the same prefix up to the first wildcard, unless
one waits for the other through After, directly or through another task; it names both tasks.
Paths with a segment named `tests`, `test`, `__tests__` or `spec` do not cause Scope overlaps
and can be shared without an After link. Explicit After links still apply.
When tasks need the same production file, put it in the first task's Scope with the shared names and stubs;
tasks that need them wait for that task through After and then own only their files. Keep a file
that a script can make at build time out of the repo and out of every Scope; when the repo keeps such
a file on purpose, give its change to one part that the others wait for. Tests: the
tests it adds or changes. After: the tasks it waits for. When two tasks share a function, field,
file format or command, the first task pins it: it commits the shared names and stubs plus one
test that crosses both sides, and the tasks that use it list it under After. Split tasks so each
owns its files; shared lines (command table, guide list, registry) go to one task or a small last
wiring task; After only when a task needs another task's code. The
Developer column is optional: the lead fills or changes a GitHub username here, below For the
builders, without another approval. Leave it blank for an unassigned part. Forge next uses
the caller's GitHub login; another developer may start it with a warning. Existing tables
without Developer still work. The moving-parts line stays last: "none", or each new dependency, service, datastore,
queue, background job or abstraction layer, with the Done-when item that needs it. -->

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| SMALL | Small test set for pull requests | `test_select = "small"`: the pytest picker runs the changed test files, the Proof list tests and the basic tests; the pull request check uses one test group; the basic-tests list gets a few end-to-end entries; `skill.md` and `brief.md` explain the setting | 1, 2, 3 | `src/forge/repo.py`, `src/forge/fasttest.py`, `src/forge/templates/review-tests.py`, `.forge/review-tests.py`, `.forge/always-tests.txt`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_small_pull_request_tests.py` (new); the existing tests named under item 2 | | no | |

New moving parts: none

## Notes

- One part, not two: the selection change, the one-group change and the guide text all depend on the same setting, and item 2 needs no code. About 30 lines of code, plus the tests, the list entries and the guide text.
- Module sizes (ceiling 1,200 lines, `test_5_forge_stays_small`): `repo.py` has 1,185 and gets at most 3 lines; `fasttest.py` has 899 and gets about 15; `review-tests.py` has 319. `close.py` (1,165), `review.py` (1,200) and `nextstep.py` (1,198) are not touched. Run the cheap repo checks from AGENTS.md before the round ends.
- Simplicity score (F x H >= 2 x C): F = 3 (every pull request), H = 2 (a slow step), C = 2 (about 30 lines and one setting). 6 is at least 4. Even with C = 3 for a new setting, 6 is at least 6.
- Why a setting and not a Forge-only change: the same slow picker hits any client repo whose tests run the real program, and AGENTS.md says process improvements ship to clients. The setting costs about 3 lines more than a hard-coded change and leaves every repo's default alone.
- Why `.forge/always-tests.txt` and not a new `.forge/smoke-tests.txt`: Forge already reads it, runs it on every code change and on docs-only changes, and tells repos about it in the guides. A second list would need new reading code and new guide text for the same job.
- Same selection for close and the check: close with `test_place = "local"` and the `tests` job both end in `fasttest.close_tests` and then `pytest_tests`, so one edit covers both. With `ci`, close waits for the `tests` check, which now runs the small set. `forge merge` retests through the same path.
- FORGE-MIXTEST-1 (approved, not built) adds `test_place = "mixed"` and a `wide` test in `fasttest.py` and `review-tests.py`. This story does not depend on it. Whichever merges second must make `wide` return false when `test_select = "small"`, because the small set is never wide. The two stories touch different functions, but read each other's diff before merging.
- Guesses to confirm with the owner. (1) The basic-tests list reuses `.forge/always-tests.txt`; you wrote "such as .forge/smoke-tests.txt" as an example. (2) The Proof list is the "Done-when / Proof list" of your words; a task's Tests column is also read for worker runs, as today. (3) This repo stays on `test_place = "ci"`, not `local`, because the nightly run on GitHub exists only for `ci` repos. This replaces the 27 Nov plan to switch back to `local` after v1.2.50, so please confirm. A `local` repo that sets `small` keeps the daily full run on its own machine, as today. (4) "Opens a fix by itself" is read as "names the exact command and the agent runs it", which is what Forge does today; no new automatic start is built. (5) The pull request check uses one group in `small` mode for every change, including a change to a shared build file, because the small set is short.
- Option B (FORGE-FUNCSEL-1, a coverage-based picker) is not built here. When it exists it replaces `small` as the better choice, and the nightly run stays.
