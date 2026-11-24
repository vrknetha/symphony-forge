# Tell clients what each Forge release changed

2 parts · Risks: none one-way; four accepted limits · New moving parts: none

## What changes for you

- Each Forge release ships its notes as a file inside Forge. The notes install with Forge and need no network. The version change of a release is the last change merged before the release is cut, and its notes cover everything merged since the previous release. Before anything is published, the release checks fail when the release has no notes file, or when shipped Forge files changed after its notes. Then the release cannot be cut. (Source: the owner's decision, 22 Nov 2026)
- The notes have fixed parts: the changes for client repos, the known issues, and the earlier known issues that this release fixes. Each change says what the agent or the owner must now do differently. Each known issue says what happens and what to do about it. (Source: the owner's decision, 22 Nov 2026)
- `forge upgrade` prints the changes of each release between the old version and the new version, then the known issues that are still open. (Source: the owner's decision, 22 Nov 2026)
- After an upgrade, the first `forge next` shows the same list once to the agent, also in the checkout where the upgrade started while the upgrade waits for its merge. The agent tells you what changed and works the new way. Later runs of `forge next` do not show it again. Each computer of the team shows the list once, when Forge on that computer moves to the newer release. (Source: the owner's decision, 22 Nov 2026)
- If Forge cannot read its notes, `forge next` prints one line that says so and continues as before.
- `forge sync` writes a "Known Forge issues" part at the end of the Forge guide that the agents read. It lists each open issue with its workaround. When a later release fixes an issue, the issue goes out of the list after the upgrade to that release. (Source: the owner's decision, 22 Nov 2026)
- The notes of v1.2.40 to v1.2.46 come from the GitHub release pages, so a repo on an older release also sees the recent changes when it upgrades.
- What each repo gets: a new repo gets the known-issues part of the guide at setup. It gets no change list, because nothing changed for it. An existing repo gets all of this on its upgrade to the release that has this story: the upgrade prints the changes since its old release (from v1.2.40), `forge next` shows them once on each computer, and the upgrade's fix adds the known-issues part to the guide. No setting changes, and no command is added.
- Not in this story: release notes on the board, notes for releases before v1.2.40, and known issues that are found after a release is published (they reach clients with the next release).

Design: none (no screen changes)

## Why

Clients do not learn what each Forge release changed. Release notes live only on GitHub, and the
upgrade, sync and next commands print none. After an upgrade, neither the agent nor the person
knows the new features, the fixes or the known issues.

An audit on 22 Nov 2026 found that the Forge guide covers most changes that agents must follow.
But nothing shows what changed after an upgrade. The notes exist only as GitHub release pages, and
an agent must know to read them. The release pages also give no workaround for a known issue, and
they do not say when a later release fixes one.

## Done when

1. **A release cannot be cut without its notes file inside Forge.**
2. **After an upgrade, the output lists the changes of every release between the old and the new version.**
3. **After an upgrade, Forge's next-step report shows the same changes once to the agent, and not again on later runs.**
4. **The shipped guide has a known-issues section with each open issue's workaround, and a fixed issue is gone after the release that fixes it.**

## Risks

<!-- Each one-way step: deleting data, a destructive migration, a new vendor. -->

Risks: none one-way. Each part reverts with its pull request. No record changes form.

Accepted limits:
- The notes are fixed when a release is published. A known issue that is found later reaches
  clients only with the next release. Today a person can still edit a GitHub release page after
  publication; the file in Forge cannot change.
- The change list prints from the new release's sync, because the upgrade command runs the old
  release's code. So the list also prints again if someone runs `forge sync` again on the
  upgrade's branch. This is harmless.
- Releases before v1.2.40 have no notes. An upgrade from an older release lists only the changes
  from v1.2.40.
- The GitHub pages of v1.2.40 to v1.2.46 give no workarounds and do not say which known issues
  were fixed later. The builder writes the workarounds now and checks each issue's fix. When a fix
  cannot be confirmed, the issue stays in the list as open.

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

Each new test runs the forge command (or reads repo files, as the release test already does) and
never imports forge. New test functions are named `test_<n>_...` after this story's Done-when
number; `tests/test_release_notes.py` starts with `STORY = "FORGE-RELNOTES-1"`. All rules are
tested on a new repo only (Review rules); the upgrade case uses the existing upgrade harness.

**What the code does today.**
- `forge upgrade` (`src/forge/upgrade.py:74`) runs the code of the release that is installed when
  it starts, which is the old release. Only two steps run the new release, through
  `repo.run_release` (`src/forge/repo.py:1013`, which sets `FORGE_PINNED_RUN`): the sync in the
  fix's folder (`upgrade.py:252`) and the close (`upgrade.py:276`). So code that this story adds
  to `upgrade.py` would not run on the first upgrade into this release; v1.2.42's own notes name
  the same problem ("The first upgrade to v1.2.42 still runs the previous release's upgrade
  code"). This story changes nothing in `upgrade.py`. The new release's `forge sync` prints the
  list, and `forge upgrade` streams that output.
- Before the sync, upgrade has already fetched the default branch (`repo.default_config`,
  `upgrade.py:116`) and set the fix's `forge.toml` to the new version (`upgrade.py:213-219`). So in
  the fix's folder, the folder's pin is the new release and `origin/<default>:forge.toml` still
  pins the old one. The starting checkout keeps the old pin until the merge.
- `forge next` has `changes_state: False` (`src/forge/nextstep.py:27`), so `cli.py:150` never runs
  `repo.check_pin` for it: `next` runs the installed release whatever the checkout pins. It reads
  settings through `repo.config` and catches a refusal so the report goes on (`nextstep.py:148`;
  `tests/test_fix_one_worktree_with_settings_the_installed.py:44` requires this).
- `forge next` prints `upgrade.release_notice(top)` and `fullrun.notices(top)` as its `notice`
  lines (`nextstep.py:154`). The daily release check keeps a per-clone cache in
  `repo.forge_dir(top)` (`.git/forge/`, shared by every worktree, never committed; `repo.py:449`).
  Nothing runs `forge next` by itself: no hook, pane or board path calls `next_step`.
- `repo._pin(text)` (`repo.py:1052`) reads only the `version` of a forge.toml text, without the
  rest of the settings; `repo.check_pin` uses it for every worktree (`repo.py:960`).
- Sync already prints a one-off upgrade message: the gpt-6.2-sol line (`src/forge/sync.py:726-732`).
  That is the kind of message release notes now carry (Notes, open question 3).
- The Forge guide copies `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md` are
  shipped by `story.ships` (`src/forge/story.py:88-108`) as the bytes of
  `src/forge/templates/skill.md`. `sync.files` (`sync.py:434`) imports every module that defines a
  top-level `ships` and refuses a path shipped twice. The commit hook's generated-file check calls
  `sync.files` too, so a module with `ships` must import fast (stdlib and `repo` only).
- `story.py` is at exactly 1,200 lines, the limit of `tests/test_rules.py::test_5_forge_stays_small`.
  `nextstep.py` is at 1,184. `src/forge/releases.py` already exists (the board's Releases page),
  so a `src/forge/releases/` folder would clash with it on import, and `src/forge/known_issues.py`
  already means kept review findings on the board. Hence the names below.
- `pyproject.toml:23` builds the wheel from `packages = ["src/forge"]`, which takes every file in
  that folder, as it does for `src/forge/templates/*.md`.
- Release process (`docs/guide.md:685-705`, "Releasing Forge"): the bump fix sets `__version__`
  and merges before the nightly runs; the cut is "the newest main commit whose Linux full run and
  Windows run passed", which can be later than the bump. The tag push runs
  `.github/workflows/forge-next.yml` (`on.push.tags: ['v*']`). The bump always changes
  `tests/test_release_version.py`, whose versions are written out, so related-test selection
  (changed test files are picked) always runs that file on a bump.
- Five tests expect the guide copies to equal the template (or the template plus the fake
  release's marker): `tests/test_generated_skill_round_rule.py:18-34`, `tests/test_split_ships.py:20`
  (`SOURCES`, compared at about line 75, and its package-copy case from about line 81),
  `tests/test_trim_skills.py:20-21`, `tests/test_upgrade_to_installed_release.py:65-69` and
  `tests/test_workers_leave_settings_to_coordinator.py:218`.

**Words this story pins.** NOTES commits these; SHOW uses them.

- Folder `src/forge/release-notes/`, one file per release: `v<x.y.z>.md`.
- File form (one bullet per line, no wrapped lines):

  ```
  # Forge v1.2.46

  ## What changes for client repos

  - <One change: what is different, and what the agent or owner does now, such as a command, a setting, or "nothing to do".>

  ## Known issues

  - **<Short title, unique across all notes files>.** <What happens and when.> Workaround: <what to do, or "none; <what to expect>">.

  ## Fixed known issues

  - **<The bold title of an earlier release's known issue, unchanged>.**
  ```

  The first heading is required and has at least one bullet. `## Known issues` and
  `## Fixed known issues` appear only when they have bullets. No other headings. No client name.
- Module `src/forge/release_notes.py` (stdlib, `forge.__version__` and `repo` only):
  - `NOTES = Path(__file__).parent / "release-notes"`
  - `releases() -> list[tuple[str, dict[str, list[str]]]]`: each notes file whose version is not
    newer than `forge.__version__`, oldest first, as `("v1.2.46", {heading: [bullet lines]})`.
    Versions compare as number tuples.
  - `TITLE = re.compile(r"^- \*\*(.+?)\*\*")`
  - `open_issues(upto: str) -> list[str]`: the `## Known issues` bullets of files up to `upto`
    whose title is under no `## Fixed known issues` of a file up to `upto`, each with
    ` (Since v<x.y.z>.)` added.
  - `ships(top, cfg) -> dict[str, str]`: the two guide copies (moved out of `story.ships`).
  - SHOW adds `changes(old, new) -> list[str]`, `upgrade_notice(top, cfg) -> None`,
    `once(top) -> tuple[list[str], str | None]` and `mark(top, version) -> None`.
- Per-clone marker (SHOW): `repo.forge_dir(top) / "release-notes-shown"`, one line with the newest
  version whose changes `forge next` showed on this clone.

### Done-when details

1. A release cannot be cut without its notes file (NOTES).
   - Write `src/forge/release-notes/v1.2.40.md` to `v1.2.46.md` (and any newer published release
     at build time) from `gh release view <tag> --repo knacklabs/symphony-forge --json body`:
     - Client-facing changes become one bullet each under `## What changes for client repos`.
       v1.2.40 has topic headings in place of that heading; turn them into bullets. Leave out the
       "Forge's own work" and "Forge's own tests" parts and the "Upgrade first, then run forge
       sync" line (the upgrade runs sync).
     - Add to each change, where it applies, what the agent or owner now does differently.
     - Each known issue gets a bold title and a `Workaround:`. For each issue, check its GitHub
       issue (when it names one) and the later release pages. When a later release in this range
       fixes it, list its title under that release's `## Fixed known issues`. When the fix cannot
       be confirmed, keep it open. v1.2.42's "first upgrade runs the previous release's upgrade
       code" is no longer true for an upgrade from v1.2.42 or later; mark it fixed in v1.2.43.
   - The bump is the last merge before the cut. In `docs/guide.md` "Releasing Forge", step 1
     becomes: `In a fix, set __version__ in src/forge/__init__.py to the new version (without the
     v) and add src/forge/release-notes/v<version>.md for everything merged since the previous
     release. Merge it last: the cut commit is this fix's merge commit. A fix that must join the
     release after it (a fix without which the release is unsafe) also updates that notes file.`
     Step 2's "the version-bump commit or a later main commit" and "the newest main commit whose
     Linux full run and Windows run passed" become the bump's merge commit (or the last joining
     fix's). Step 3 starts with: `Before you create the tag, run python
     .github/release-notes-check.py vX.Y.Z <full cut SHA>. When it fails, do not tag: add the
     missing change to the notes in a fix, merge it, and use its merge commit as the cut.` Step 4
     ends with: `Publish the GitHub release with gh release create vX.Y.Z --notes-file
     src/forge/release-notes/vX.Y.Z.md.` So both checks run before anything is public: the bump
     pull request's own CI runs `tests/test_release_version.py` (every bump edits it), which
     proves the notes file for the new version exists, and the script runs on the commit to be
     tagged before `git tag`. No workflow changes.
   - The release check: `.github/release-notes-check.py <tag> <commit>` (new, stdlib, in the style
     of `.github/reuse-test-proof.py`). Its shipped paths are `src/forge` and every source path
     under `[tool.hatch.build.targets.wheel.force-include]` in `pyproject.toml` at `<commit>`
     (`tomllib`). It exits 1 with one line when `src/forge/release-notes/<tag>.md` is missing at
     `<commit>` (`Release <tag> has no notes file src/forge/release-notes/<tag>.md.`), or when the
     newest commit up to `<commit>` that changes a shipped path
     (`git log -1 --format=%H <commit> -- <shipped paths>`) is not a commit that changes that notes
     file (`Shipped Forge files changed after the notes of <tag>: <short sha> <subject>. Add it to
     the notes, then run this check again.`). Otherwise it prints `Release <tag> notes cover
     <short commit>.` and exits 0.
   - Add to this repo's `AGENTS.md`, in "Building Forge (this repo only)" (Forge's own release
     process, not a client rule), this bullet: `Each release bump adds
     src/forge/release-notes/v<version>.md for everything merged since the previous release, and
     merges last before the cut. Write each line for an agent that must act on it: what changed,
     and what the agent or owner now does differently. Each known issue starts with a short bold
     title, says what happens, and ends with Workaround: <what to do>, or Workaround: none; <what
     to expect>. When a release fixes an earlier known issue, list that issue's bold title,
     unchanged, under Fixed known issues. Leave out Forge's own tests and work, and name no
     client. Before tagging, run .github/release-notes-check.py on the cut commit.`
   - Test (Forge's own files): `tests/test_release_version.py::test_3_the_release_ships_notes_an_agent_can_act_on`.
     It lives in the release test because every bump changes that file, so CI always runs it on a
     bump; it takes the next free number under that file's `STORY`. It reads the version from
     `forge --version` (no version written in the test), so later bumps do not edit it. It checks:
     - `src/forge/release-notes/<version>.md` exists; every notes file's first line is
       `# Forge <its file name's version>`; only the three headings, in order; at least one bullet
       under `## What changes for client repos`; every known-issue bullet matches `TITLE` and
       holds `Workaround:`; known-issue titles are unique; every fixed title is a known-issue
       title of an earlier file.
     - The release check, run with `sys.executable` in a temporary git repo with a `src/forge`
       folder and a `pyproject.toml` whose force-include names `.codex/skills/x/SKILL.md`: the
       commit that adds `src/forge/__init__.py` and `src/forge/release-notes/v9.9.9.md` passes; a
       later commit that changes `src/forge/app.py` fails with the "changed after the notes" line;
       a later commit that changes only `.codex/skills/x/SKILL.md` fails the same way; a commit
       with no notes file fails with the "has no notes file" line.
     The proof list also names one check: `uv build --wheel` lists
     `forge/release-notes/v1.2.46.md` in the wheel.
2. The upgrade prints the changes between the old and the new release (SHOW).
   - `release_notes.upgrade_notice(top, cfg)`, called once at the end of `sync.sync` (after its
     `Wrote` lines): `old` is `repo._pin` of
     `repo.read_blob(top, f"origin/{repo.default_branch(top)}:forge.toml")` (no fetch), `new` is
     `cfg["version"]`. Only when both read and `new` is newer than `old`, print
     `changes(old, new)`. It writes nothing. Anything unreadable: print nothing. Nothing in
     `upgrade.py` changes.
   - `changes(old, new)`, `[]` when no notes file is newer than `old` and not newer than `new`:

     ```
     Forge changed from v1.2.44 to v1.2.46. Tell the owner what changed, in plain words, and work the new way:
     Forge v1.2.45:
     - <each change bullet>
     - Fixed known issue: <title>
     Forge v1.2.46:
     - ...
     Open known Forge issues in v1.2.46, with what to do:
     - <each open_issues(new) bullet>
     ```

     The last part is left out when no issue is open.
   - Test harness: the fake uv in `tests/test_upgrade_command.py` copies the files of
     `<bin>/extra-notes/` (when that folder exists) into the fake release's
     `src/forge/release-notes/` after its copy (two lines in the `UV` text).
   - Test (new repo): `tests/test_release_notes.py::test_2_upgrade_lists_the_changes_of_every_release_between`.
     The `up` fixture (fake uv, release `v9.9.9`). `extra-notes/v9.9.8.md` has the change
     `- Test change eight.` and the known issue `- **Test issue one.** It fails. Workaround: run it again.`;
     `extra-notes/v9.9.9.md` has `- Test change nine.`, lists `**Test issue one.**` as fixed and
     has `- **Test issue two.** It waits. Workaround: none; it ends in a minute.`.
     `up.on_main("forge.toml", ...)` pins `v1.2.44`, as `tests/test_upgrade_to_installed_release.py`
     pins `v1.0.0`. `up.run(RELEASE)` exits 0, and its output has, in order:
     - `Forge changed from v1.2.44 to v9.9.9. ...`;
     - `Forge v1.2.45:` followed by each `## What changes for client repos` bullet of the real
       `src/forge/release-notes/v1.2.45.md`, read by the test;
     - `Forge v9.9.8:`, `- Test change eight.`, `Forge v9.9.9:`, `- Test change nine.`,
       `- Fixed known issue: Test issue one`;
     - the open-issues line and `- **Test issue two.** It waits. Workaround: none; it ends in a minute. (Since v9.9.9.)`;
     and no `Forge v1.2.44:` and no open-issues line with `Test issue one`.
3. `forge next` shows the same list once on each clone (SHOW).
   - `release_notes.once(top) -> tuple[list[str], str | None]` (the lines, and the version to mark
     as shown) writes nothing. `nextstep.next_step` adds the lines to its `notice`
     (`nextstep.py:154`) and, after its final `print`, calls `release_notes.mark(top, version)`
     when the version is not `None` (two lines). So a report that fails before it prints marks
     nothing. `once` reads pins only with `repo._pin` of the forge.toml texts, never
     `repo.config`, so settings the installed release cannot read do not matter:
     - `target`: the newest pin among this checkout and every worktree of the clone
       (`story.worktrees(top)`; the upgrade's fix folder pins the new release while it waits),
       but not newer than `forge.__version__` (the running release has no newer notes). A clone
       whose installed release is older than its pin waits, and shows the list when that release
       is installed.
     - `base`: the marker's version. When there is no marker, the newest pin older than `target`
       among this checkout's `forge.toml` and its versions in
       `git log -n 200 --format=%H -- forge.toml` (each read with `repo.read_blob`). A new repo has
       none: return `([], target)`, so nothing shows and the marker is set. A new clone of an
       upgraded repo finds the pin before the upgrade, so it shows the list once.
     - When `target` is newer than `base`: return `(changes(base, target), target)`. Otherwise
       `([], None)`.
     - Any error (OS, git, value): return `(["Forge could not read its release notes (<first line
       of the error>)."], None)`; nothing is marked and `forge next` goes on as before.
     - `mark(top, version)` writes the version to the marker and ignores an `OSError`.
   - Text: one sentence in `src/forge/templates/skill.md` "Upgrade Forge" (`:1573`): `After an
     upgrade, forge upgrade and then forge next (once on each computer) list what changed in each
     release and the open known Forge issues. Tell the owner the changes that affect them in plain
     words, follow each line's instruction, and read the "Known Forge issues" part at the end of
     this guide.` Copy over both repo copies of the guide with `forge sync`.
   - Test (new repo): `tests/test_release_notes.py::test_3_next_shows_the_changes_once_after_an_upgrade`,
     on the test 2 setup. "The list" below is the v9.9.8 and v9.9.9 lines that test 2 checks.
     `forge next` "as the installed release" runs `tmp/uvbin/forge`, the launcher the fake install
     put on PATH (the v9.9.9 copy). Parametrized:
     - `starting-checkout`: `forge next` as the installed release in `up.repo.path` (still pinned
       `v1.2.44`, the upgrade not merged) prints the list; a second run prints none of it.
     - `older-release-first`: `repo.forge("next", cwd=up.folder)` (this checkout's release, older
       than the folder's `v9.9.9` pin) prints none of the v9.9.x lines; then `forge next` as the
       installed release in `up.folder` prints the list, and a second run prints none of it.
     - `new-clone`: after `up.on_main("forge.toml", <pin v9.9.9>)`, a `git clone` of the origin;
       `forge next` as the installed release in the clone prints the list once, and not on a
       second run.
     - `new-repo`: a new repo (`_fresh_client` of `tests/test_setup.py`); `forge next` twice; no
       output has `Forge changed from`.
     - `unreadable-notes`: after the upgrade finishes (its sync needs readable notes), overwrite
       `tmp/releases/v9.9.9/src/forge/release-notes/v9.9.9.md`, the copy that the installed
       launcher runs, with bytes that are not valid UTF-8. `forge next` as the installed release
       in `up.folder` exits 0, prints `Forge could not read its release notes` once and still
       prints its usual next step; after the file is restored, the next run prints the list (the
       failed run marked nothing).
4. The guide's known-issues part (NOTES).
   - `release_notes.ships(top, cfg)` returns `.claude/skills/forge/SKILL.md` and
     `.codex/skills/forge/SKILL.md` as the template's text plus this part at its end
     (`skill.rstrip("\n") + "\n\n" + part + "\n"`). The part names no version, so it is the same
     text for every release that has the same open issues:

     ```
     ## Known Forge issues

     Open known issues in this Forge release, from its release notes. When one affects the work, tell the owner and use its workaround. An upgrade to a release that fixes an issue removes it from this list.

     - <each open_issues(forge.__version__) bullet>
     ```

     With no open issue, the list is the one line `This Forge release has no open known issues.`
   - `story.ships` loses its `skill` line and the two guide entries (three lines out of
     `story.py`).
   - Run `forge sync` and commit this repo's regenerated guide copies
     (`tests/test_release_version.py::test_2_release_checkout_generated_files_match_sync` checks
     them).
   - Change the five guide tests listed in "What the code does today" to expect the template text
     plus the part: the part is the text that follows the template in this repo's committed
     `.claude/skills/forge/SKILL.md`. In `tests/test_upgrade_to_installed_release.py`, the
     expected text is the template with the fake release's marker, then the part. Nothing else in
     those tests changes. Before close, also run every test file that names `templates/skill.md`
     (`grep -l "templates/skill.md" tests/test_*.py`).
   - Test (new repo): `tests/test_release_notes.py::test_4_the_guide_lists_open_issues_and_drops_fixed_ones`.
     As `tests/test_codex_model_upgrade_notice.py:33-39` does, copy `src/forge` to a temporary
     package and install it as `forge` with `FORGE_SHIM`:
     - Package version `9.9.8` with an added `release-notes/v9.9.8.md` that has a known issue
       `**Test issue one.** ... Workaround: run the check again.`. `forge init` in a new repo
       (`_fresh_client`): both guide copies end with the "Known Forge issues" part, which holds
       that line with its workaround and `(Since v9.9.8.)`.
     - The same package at version `9.9.9` with an added `v9.9.9.md` that lists `**Test issue
       one.**` under `## Fixed known issues` and has a known issue `**Test issue two.**`. On a fix
       branch whose `forge.toml` pins `v9.9.9`, `forge sync` rewrites both copies: issue two is in
       the list, issue one is not.

### New and existing repos

- **New repos** (`forge init`): the "Known Forge issues" part in both guide copies. `forge next`
  writes its marker on its first run and shows no change list.
- **Existing repos** (on upgrade to the release with this story): the old release's upgrade code
  runs the new release's sync, which prints the change list from the old pin (notes start at
  v1.2.40); `forge next` shows the list once on each clone, in the starting checkout while the
  upgrade waits and on teammates' clones when their Forge moves to the release; the upgrade's fix
  commits the guide copies with the new part. No record changes form;
  `tests/test_upgrade_to_installed_release.py` changes only its expected guide text.
- **Forge's own repo:** each release bump adds its notes file and merges last; the bump's CI fails
  without the file, and the release check before the tag fails when shipped files changed after
  the notes.

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
| NOTES | Release notes files, the release gate and the guide's known issues | The notes file form; notes for v1.2.40 to v1.2.46 from the GitHub release pages, with workarounds and fixed marks; the release test that fails without the current release's notes; the release check, run on the cut commit before the tag, that fails when the notes file is missing or shipped Forge files changed after it; the bump-merges-last release order; the reader of the notes files; the "Known Forge issues" part at the end of both guide copies, which drops an issue once a release fixes it; the release-notes rule in this repo's AGENTS.md | 1, 4 | `src/forge/release-notes/` (new), `src/forge/release_notes.py` (new), `src/forge/story.py` (`ships` only), `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `.github/release-notes-check.py` (new), `docs/guide.md` ("Releasing Forge" only), `AGENTS.md` ("Building Forge (this repo only)" only), `tests/test_generated_skill_round_rule.py`, `tests/test_split_ships.py`, `tests/test_trim_skills.py`, `tests/test_upgrade_to_installed_release.py`, `tests/test_workers_leave_settings_to_coordinator.py` (the expected guide text only) | `tests/test_release_version.py::test_3_the_release_ships_notes_an_agent_can_act_on`, `tests/test_release_notes.py::test_4_the_guide_lists_open_issues_and_drops_fixed_ones` (new) | | no | |
| SHOW | Show the changes after an upgrade | The new release's sync prints the changes of every release between the default branch's pin and the new pin, then the open known issues, which `forge upgrade` streams; `forge next` shows the same list once on each clone (starting checkout during the upgrade, teammates' clones, new clones) through a marker in `.git/forge/` and the pin history of forge.toml, and prints one line and goes on when it cannot read the notes; one sentence in the guide's Upgrade Forge part | 2, 3 | `src/forge/release_notes.py`, `src/forge/sync.py` (one call at the end of `sync`), `src/forge/nextstep.py` (the `notice` line and the `mark` call after the final print only), `src/forge/templates/skill.md` (Upgrade Forge only), `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `tests/test_upgrade_command.py` (the `extra-notes` lines of `UV` only) | `tests/test_release_notes.py::test_2_upgrade_lists_the_changes_of_every_release_between`, `tests/test_release_notes.py::test_3_next_shows_the_changes_once_after_an_upgrade` (new) | NOTES | no | |

New moving parts: none

## Notes

- **Order.** NOTES first: it pins the file form, `release_notes.py` and its reader. SHOW waits for
  NOTES (same module and the same guide copies).
- **Size.** NOTES is about 85 changed lines of code outside tests and Markdown (the notes files are
  Markdown; the release check script is about 30 of them). SHOW is about 60. `story.py` goes from
  1,200 to 1,197 lines and `nextstep.py` from 1,184 to 1,186.
- **Why sync prints the list, not upgrade.** See "What the code does today": the upgrade command
  runs the old release's code, and only the new release's sync and close run new code. Printing
  from the new sync works on the first upgrade into this release and on every later one, with no
  change to `upgrade.py`.
- **Why the marker and the pin history.** The marker keeps the list to once per clone. The newest
  pin across the clone's worktrees shows it in the starting checkout while the upgrade waits. The
  cap at the running release keeps a clone with an older Forge from skipping notes it cannot see.
  The forge.toml pin history gives a clone with no marker (a teammate, a new clone) the pin before
  the upgrade, so no clone misses the list.
- **Choices made for the owner to confirm.**
  1. The upgrade output and `forge next` also list the open known issues, not only the changes. The
     owner's decision names the changes; the agent needs the open issues to adjust too.
  2. The guide part is called "Known Forge issues", because the board already uses "known issues"
     for kept review findings (`src/forge/known_issues.py`).
  3. The bump merges last and the cut is its merge commit, in place of "the newest main commit
     whose runs passed" (cold read 1, note 3).
- **Open questions for the owner.**
  1. Backfill: older known issues whose fix the builder cannot confirm stay listed as open. Accept,
     or carry only the known issues of v1.2.46's page?
  2. The GitHub release page is made from the notes file (`gh release create --notes-file`), so the
     file is the one home of the notes. Accept?
  3. The gpt-6.2-sol message in sync (`sync.py:726-732`) is a release note. Move it into the next
     release's notes and delete it from sync, in a separate fix after this story?
- **Open questions for the builders.**
  1. Confirm that `uv build --wheel` puts `forge/release-notes/*.md` in the wheel (it takes every
     file under `src/forge`).
- **Changes no setting and adds no command.** The guide carries the new step.
- No client repo is named anywhere in this story's code, tests, notes files or commits.
