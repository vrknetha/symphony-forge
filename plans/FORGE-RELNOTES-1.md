# Tell clients what each Forge release changed

2 parts · Risks: none one-way; five accepted limits · New moving parts: none

## What changes for you

- Each Forge release ships its notes as a file inside Forge. The notes install with Forge and need no network. Forge's release test fails when the release has no notes file, so the release cannot be cut. (Source: the owner's decision, 22 Nov 2026)
- The notes have fixed parts: the changes for client repos, the known issues, and the earlier known issues that this release fixes. Each change says what the agent or the owner must now do differently. Each known issue says what happens and what to do about it. (Source: the owner's decision, 22 Nov 2026)
- `forge upgrade` prints the changes of each release between the old version and the new version, then the known issues that are still open. (Source: the owner's decision, 22 Nov 2026)
- After an upgrade, the first `forge next` on that computer shows the same list once to the agent. The agent tells you what changed and works the new way. Later runs of `forge next` do not show it again. (Source: the owner's decision, 22 Nov 2026)
- `forge sync` writes a "Known Forge issues" part at the end of the Forge guide that the agents read. It lists each open issue with its workaround. When a later release fixes an issue, the issue goes out of the list after the upgrade to that release. (Source: the owner's decision, 22 Nov 2026)
- The notes of v1.2.40 to v1.2.46 come from the GitHub release pages, so a repo on an older release also sees the recent changes when it upgrades.
- What each repo gets: a new repo gets the known-issues part of the guide at setup. It gets no change list, because nothing changed for it. An existing repo gets all of this on its upgrade to the release that has this story: the upgrade prints the changes since its old release (from v1.2.40), `forge next` shows them once, and the upgrade's fix adds the known-issues part to the guide. No setting changes, and no command is added.
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
- `forge next` remembers on each computer which release it showed last. A teammate's computer
  that never ran `forge next` with this release shows nothing for the first upgrade. From the
  next upgrade, it shows the changes once when that teammate's checkout moves to the newer
  release. The guide's known-issues part reaches every teammate through the committed guide.
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
  pins the old one.
- Sync already prints a one-off upgrade message: the gpt-6.2-sol line (`src/forge/sync.py:726-732`).
  It prints on every sync while the condition holds. That is the kind of message release notes now
  carry (Notes, open question 4).
- `forge next` (`src/forge/nextstep.py:144`) prints `upgrade.release_notice(top)` and
  `fullrun.notices(top)` as its `notice` lines (`nextstep.py:154`). The daily release check keeps a
  per-clone cache in `repo.forge_dir(top)` (`.git/forge/`, shared by every worktree, never
  committed; `repo.py:449`). Nothing runs `forge next` by itself: no hook, pane or board path
  calls `next_step` (only the CLI table in `cli.py:27`).
- While the upgrade fix waits for its merge, commands on the default branch run the newly
  installed release, not the old pin (`repo.check_pin`, `repo.py:966-975`).
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
- The release bump is a fix that changes about 20 version references
  (`git show 882433996 --stat`). It always changes `tests/test_release_version.py`, whose
  versions are written out, so related-test selection (`fasttest.related`, changed test files are
  picked) always runs that file on a bump.
- Two tests compare the guide copies byte for byte with the template:
  `tests/test_generated_skill_round_rule.py:18-34` and the `skills/forge/SKILL.md` entry of
  `SOURCES` in `tests/test_split_ships.py:20` (compared at about line 75).

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
  - SHOW adds `changes(old, new) -> list[str]`, `upgrade_notice(top, cfg) -> None` and
    `once(top) -> list[str]`.
- Per-clone marker (SHOW): `repo.forge_dir(top) / "release-notes-shown"`, one line with the last
  version whose changes `forge next` showed.

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
   - Add to this repo's `AGENTS.md`, in "Building Forge (this repo only)" (Forge's own release
     process, not a client rule), this bullet: `Each release bump adds
     src/forge/release-notes/v<version>.md, and the GitHub release uses that file as its notes
     (gh release create v<version> --notes-file src/forge/release-notes/v<version>.md). Write each
     line for an agent that must act on it: what changed, and what the agent or owner now does
     differently. Each known issue starts with a short bold title, says what happens, and ends
     with Workaround: <what to do>, or Workaround: none; <what to expect>. When a release fixes an
     earlier known issue, list that issue's bold title, unchanged, under Fixed known issues. Leave
     out Forge's own tests and work, and name no client. The release test fails without the file.`
   - Test (Forge's own files): `tests/test_release_version.py::test_3_the_release_ships_notes_an_agent_can_act_on`.
     It lives in the release test because every bump changes that file, so CI always runs it on a
     bump; it takes the next free number under that file's `STORY`. It reads the version from
     `forge --version` (no version written in the test), so later bumps do not edit it. It checks:
     `src/forge/release-notes/<version>.md` exists; every notes file's first line is
     `# Forge <its file name's version>`; only the three headings, in order; at least one bullet
     under `## What changes for client repos`; every known-issue bullet matches `TITLE` and holds
     `Workaround:`; known-issue titles are unique; every fixed title is a known-issue title of an
     earlier file. The proof list also names one check: `uv build --wheel` lists
     `forge/release-notes/v1.2.46.md` in the wheel.
2. The upgrade prints the changes between the old and the new release (SHOW).
   - `release_notes.upgrade_notice(top, cfg)`, called once at the end of `sync.sync` (after its
     `Wrote` lines): `old` is the pin in `repo.read_blob(top, f"origin/{repo.default_branch(top)}:forge.toml")`
     (no fetch; `repo._pin`), `new` is `cfg["version"]`. Only when both read and `new` is newer
     than `old`: print `changes(old, new)`, and write `old` to the marker when the marker is
     missing (so `forge next` shows the list after the merge). Anything unreadable: print
     nothing. Nothing in `upgrade.py` changes.
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
   - Test (new repo): `tests/test_release_notes.py::test_2_upgrade_lists_the_changes_of_every_release_between`.
     The `up` fixture of `tests/test_upgrade_command.py` (fake uv, release `v9.9.9`, whose copy of
     `src/forge` includes the real notes files). `up.on_main("forge.toml", ...)` pins `v1.2.44`,
     as `tests/test_upgrade_to_installed_release.py` pins `v1.0.0`. `up.run(RELEASE)` exits 0;
     its output has `Forge changed from v1.2.44 to v9.9.9.`, `Forge v1.2.45:` and `Forge v1.2.46:`,
     and no `Forge v1.2.44:`.
3. `forge next` shows the same list once (SHOW).
   - `release_notes.once(top)`, added to `nextstep.next_step`'s `notice` (`nextstep.py:154`, one
     line): `[]` when the checkout has no `forge.toml`. `pin` is `repo.config(top)["version"]`.
     When the marker is missing: write `pin`, return `[]` (a new repo or a new clone shows
     nothing). When `pin` is newer than the marker: return `changes(marker, pin)` and write `pin`.
     Otherwise `[]`. A marker read or write error returns `[]`, as `release_notice` does.
   - Text: one sentence in `src/forge/templates/skill.md` "Upgrade Forge" (`:1573`): `After an
     upgrade, forge upgrade and then forge next (once on each computer) list what changed in each
     release and the open known Forge issues. Tell the owner the changes that affect them in plain
     words, follow each line's instruction, and read the "Known Forge issues" part at the end of
     this guide.` Copy over both repo copies of the guide with `forge sync`.
   - Test (new repo): `tests/test_release_notes.py::test_3_next_shows_the_changes_once_after_an_upgrade`,
     parametrized:
     - `after-upgrade`: the test 2 setup, then `forge next` in `up.folder` twice. The first output
       has `Forge changed from v1.2.44 to v9.9.9.` once; the second has none.
     - `new-repo`: a new repo (`_fresh_client` of `tests/test_setup.py`); `forge next` twice; no
       output has `Forge changed from`.
4. The guide's known-issues part (NOTES).
   - `release_notes.ships(top, cfg)` returns `.claude/skills/forge/SKILL.md` and
     `.codex/skills/forge/SKILL.md` as the template's text plus this part at its end
     (`skill.rstrip("\n") + "\n\n" + part + "\n"`):

     ```
     ## Known Forge issues

     Open known issues in Forge v1.2.46, from its release notes. When one affects the work, tell the owner and use its workaround. An upgrade to a release that fixes an issue removes it from this list.

     - <each open_issues(forge.__version__) bullet>
     ```

     With no open issue, the list is the one line `Forge v1.2.46 has no open known issues.`
   - `story.ships` loses its `skill` line and the two guide entries (three lines out of
     `story.py`).
   - Run `forge sync` and commit this repo's regenerated guide copies
     (`tests/test_release_version.py::test_2_release_checkout_generated_files_match_sync` checks
     them).
   - Change the two byte-for-byte tests to compare the guide copies with this repo's committed
     `.claude/skills/forge/SKILL.md` (sync output) in place of the template; nothing else in them
     changes. Before close, also run every test file that names `templates/skill.md`
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
  v1.2.40) and writes the marker; `forge next` shows the list once; the upgrade's fix commits the
  guide copies with the new part. No record changes form, so
  `tests/test_upgrade_to_installed_release.py` does not change.
- **Forge's own repo:** each release bump adds its notes file; the release test fails without it.

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
| NOTES | Release notes files and the guide's known issues | The notes file form; notes for v1.2.40 to v1.2.46 from the GitHub release pages, with workarounds and fixed marks; the release test that fails without the current release's notes; the reader of the notes files; the "Known Forge issues" part at the end of both guide copies, which drops an issue once a release fixes it; the release-notes rule in this repo's AGENTS.md | 1, 4 | `src/forge/release-notes/` (new), `src/forge/release_notes.py` (new), `src/forge/story.py` (`ships` only), `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `AGENTS.md` ("Building Forge (this repo only)" only), `tests/test_generated_skill_round_rule.py` and `tests/test_split_ships.py` (the guide's expected source only) | `tests/test_release_version.py::test_3_the_release_ships_notes_an_agent_can_act_on`, `tests/test_release_notes.py::test_4_the_guide_lists_open_issues_and_drops_fixed_ones` (new) | | no | |
| SHOW | Show the changes after an upgrade | The new release's sync prints the changes of every release between the default branch's pin and the new pin, then the open known issues, which `forge upgrade` streams; `forge next` shows the same list once per computer through a marker in `.git/forge/`; one sentence in the guide's Upgrade Forge part | 2, 3 | `src/forge/release_notes.py`, `src/forge/sync.py` (one call at the end of `sync`), `src/forge/nextstep.py` (the `notice` line only), `src/forge/templates/skill.md` (Upgrade Forge only), `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_release_notes.py::test_2_upgrade_lists_the_changes_of_every_release_between`, `tests/test_release_notes.py::test_3_next_shows_the_changes_once_after_an_upgrade` (new) | NOTES | no | |

New moving parts: none

## Notes

- **Order.** NOTES first: it pins the file form, `release_notes.py` and its reader. SHOW waits for
  NOTES (same module and the same guide copies).
- **Size.** NOTES is about 60 changed lines of code outside tests and Markdown (the notes files are
  Markdown). SHOW is about 45. `story.py` goes from 1,200 to 1,197 lines and `nextstep.py` from
  1,184 to 1,185.
- **Why sync prints the list, not upgrade.** See "What the code does today": the upgrade command
  runs the old release's code, and only the new release's sync and close run new code. Printing
  from the new sync works on the first upgrade into this release and on every later one, with no
  change to `upgrade.py`.
- **Why a version marker, not a "shown" flag file.** A file that sync writes and next deletes would
  reach only the computer that ran the upgrade. The version marker also shows the list on a
  teammate's computer when the teammate's checkout moves to a newer release (from the second
  release with this story; Accepted limits).
- **Choices made for the owner to confirm.**
  1. The upgrade output and `forge next` also list the open known issues, not only the changes. The
     owner's decision names the changes; the agent needs the open issues to adjust too.
  2. The guide part is called "Known Forge issues", because the board already uses "known issues"
     for kept review findings (`src/forge/known_issues.py`).
- **Open questions for the owner.**
  1. A teammate's computer shows nothing for the first upgrade with this story (Accepted limits).
     Accept, or have `forge next` find the previous pin from git history (more code)?
  2. Backfill: older known issues whose fix the builder cannot confirm stay listed as open. Accept,
     or carry only the known issues of v1.2.46's page?
  3. Should the GitHub release page be the notes file (`gh release create --notes-file`), so the
     file is the one home of the notes? The AGENTS.md rule above assumes yes.
  4. The gpt-6.2-sol message in sync (`sync.py:726-732`) is a release note. Move it into the next
     release's notes and delete it from sync, in a separate fix after this story?
- **Open questions for the builders.**
  1. Confirm that `uv build --wheel` puts `forge/release-notes/*.md` in the wheel (it takes every
     file under `src/forge`).
  2. `tests/test_split_ships.py`'s package-copy case (from about line 81) may also compare the guide
     with the template; change it the same way if it does.
- **Changes no setting and adds no command.** The guide carries the new step.
- No client repo is named anywhere in this story's code, tests, notes files or commits.
