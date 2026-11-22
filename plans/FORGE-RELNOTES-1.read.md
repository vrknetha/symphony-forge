---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-22T18:38:52.818115+00:00
seconds: 482.788
read_hash: 09efa1332bec19da7a7494cd3ba8b05382b4d3e7
round: 3
passed: no
doc_seen: 09efa1332bec19da7a7494cd3ba8b05382b4d3e7
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: c183ab7fdb794d1b3aac1aa7f0051a6eff80bbf8
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a20460-af65-7c02-b859-7b2618e0c7a4
session:
loop_choice: accept
loop_reason: Owner accepted on 23 Nov 2026: the builder starts the release check with uv run --frozen --python 3.11 python instead of python; advisory 13 stays for the builders; no plan edit
---
# Cold read notes

Written by `forge read`. Under every blocking finding, write one disposition line, amend the
doc, then run `forge read <doc>` again until a round has no blocking notes. Notes marked
`Advisory:` are recorded without requiring a disposition or another round:

- `Disposition: cut` when the doc was edited to remove it;
- `Disposition: defer` when the item moved to the spec's Out of scope;
- `Disposition: keep <one-line reason>` otherwise.

A finding inside What counts is cut or deferred. Keep one only when it falls outside that boundary
or is factually wrong or not worth the change, and give as the reason the Leave out line, the
missing Raise line, the cited fact that disproves it, why it is not worth the change, or the
human's `Decided:` line.

Only a genuine trade-off goes to the human, as a question with options.

## Round 1

1. Blocking: Not done: item 3: A teammate can permanently miss an upgrade’s notes.
   Raise: Functional  
   Case: normal use - A teammate updates their checkout after an upgrade but still has the previous Forge release installed.  
   `forge next` does not check the installed version against the checkout’s pin ([nextstep.py](/src/forge/nextstep.py:27), [cli.py](/src/forge/cli.py:150)). The planned reader cannot see notes newer than the installed release, but it still advances the marker to the checkout’s newer version ([plan](/plans/FORGE-RELNOTES-1.md:136), [marker rule](/plans/FORGE-RELNOTES-1.md:211)). A later run with the new release will therefore not show the missed notes.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - next now caps the shown release at the running Forge and writes only that, and a clone with no marker takes its base from the forge.toml pin history, so no clone misses the list (Done-when 3 details; test cases older-release-first and new-clone).

2. Blocking: Not done: item 3: The first `forge next` in the starting checkout does not show the upgrade.
   Raise: Functional  
   Case: normal use - The coordinator runs `forge upgrade`, then `forge next` while the upgrade pull request waits for its merge.  
   Upgrade changes the pin in its separate worktree, leaving the starting checkout’s pin unchanged ([upgrade.py](/src/forge/upgrade.py:213)). The planned marker and that checkout’s pin both hold the old version, so the next report shows no change list. The proposed test runs `next` in the upgrade worktree and misses this path ([plan](/plans/FORGE-RELNOTES-1.md:221)).  
   Gain 4, Work 2, Harm 3
   Disposition: cut - the shown release is the newest pin across the clone's worktrees, so the starting checkout shows the list while the upgrade fix waits (test case starting-checkout).

3. Blocking: Not done: item 2: Release notes can omit work merged after the version bump.
   Raise: Plan gap  
   Case: normal use - A client-facing fix or story merges after the version-bump fix and before the daily release cut.  
   The release process permits the cut to use a later main commit than the version-bump commit ([release guide](/docs/guide.md:696)). The plan creates the notes at the bump but gives no task or release step to bring them up to date through the cut ([plan](/plans/FORGE-RELNOTES-1.md:164)). The nonempty-file test would still pass while the later change is absent.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - the bump now merges last and the cut is its merge commit (docs/guide.md Releasing Forge), and a tag check fails when the notes file is missing or Forge code merged after it (Done-when 1 details and test).

4. Blocking: Plan gap: Appending to the guide breaks existing tests outside the stated scope.
   Raise: Gate  
   Case: normal use - The builder runs the required checks after adding the known-issues section.  
   The plan permits changes to two guide comparisons and says the installed-release upgrade test does not change ([plan](/plans/FORGE-RELNOTES-1.md:243)). But [the package delivery test](/tests/test_trim_skills.py:20), [the installed-release upgrade test](/tests/test_upgrade_to_installed_release.py:65), and [the settings merge test](/tests/test_workers_leave_settings_to_coordinator.py:218) also require the shipped guide to equal the unappended template. They need changes for the planned output to pass.  
   Gain 4, Work 2, Harm 2
   Disposition: cut - all five guide tests are now in NOTES' Scope with their new expected text, and the upgrade test's change is stated.

5. Blocking: Unproven: item 3: The new notice can stop `forge next` when a worktree has unsupported settings.
   Raise: Functional  
   Case: normal use - A developer runs `forge next` in a worktree whose settings the installed Forge cannot read.  
   The planned notice reads `repo.config` without a rule for its refusal ([plan](/plans/FORGE-RELNOTES-1.md:211)). Today `next` catches that refusal and continues the report ([nextstep.py](/src/forge/nextstep.py:148)); an [existing command test](/tests/test_fix_one_worktree_with_settings_the_installed.py:44) requires that behavior.  
   Adds work: skip the notice when settings cannot be read; F 2 x H 2 = 4; 2 x C = 2.  
   Gain 4, Work 1, Harm 3
   Disposition: cut - the notice reads pins only with repo._pin, never repo.config, and any error prints one line while next goes on (test case unreadable-notes).

6. Blocking: Unproven: items 2 and 3: The proposed tests do not check the change lists.
   Raise: Test  
   Case: normal use - An upgrade includes changes and open issues in its notes.  
   The upgrade test checks version headings, and the `next` test checks only the introductory line ([plan](/plans/FORGE-RELNOTES-1.md:204)). Both would pass if the commands omitted every change, fixed issue, and open issue.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - test 2 checks each printed change, fixed issue and open issue from controlled notes files and the real v1.2.45 bullets, and test 3 checks the same lines once.

## Round 2

7. Blocking: The release check runs after the release tag is public.
   Raise: Functional  
   Case: normal use - A release-blocking fix changes Forge after the notes were written, and its notes update was missed.  
   The new check runs only after the tag is pushed ([plan](/plans/FORGE-RELNOTES-1.md:176)). Forge’s releases are the public Git tags themselves ([decision](/docs/decisions/0093-lean-forge-rebuild.md:73)); delaying the GitHub release page does not prevent installation from the tag. The existing pre-push gate checks the full test run and tag commit, but does not run the new check ([githooks.py](/src/forge/githooks.py:149)).  
   Gain 5, Work 3, Harm 3
   Disposition: cut - the tag-push step is dropped; the bump pull request's CI proves the notes file exists, and docs/guide.md runs .github/release-notes-check.py on the cut commit before git tag and before gh release create (Done-when 1 details).

8. Advisory: The new tag check ignores shipped Forge files outside `src/forge`.
   Raise: Functional  
   The check looks only for commits changing `src/forge` ([plan](/plans/FORGE-RELNOTES-1.md:179)). A later change to the Mac installer or to an agent skill included in the package can therefore be omitted from the notes while the check passes. The package includes several such skills from outside that folder ([pyproject.toml](/pyproject.toml:24)).  
   Gain 3, Work 3, Harm 3
   Disposition: cut - the release check now covers src/forge and every force-include source path in pyproject.toml (Done-when 1 details and test case).

9. Advisory: Pin history can skip releases a teammate has not seen.
   Raise: Functional  
   Case: normal use - A teammate has not used their clone while the repo moves through several daily Forge releases.  
   With no marker, the plan chooses the newest older pin in the repo’s history ([plan](/plans/FORGE-RELNOTES-1.md:255)). If the teammate last used v1.2.44 and the repo subsequently moved through v1.2.45 and v1.2.46 before reaching the new release, it chooses v1.2.46 and omits the earlier changes. The shared Git history does not say which releases that computer saw.  
   Gain 4, Work 3, Harm 2
   Disposition: keep - a clone with no marker has no record of which releases it saw, so it shows the last upgrade's list; the committed guide's Known Forge issues part still lists every open issue, and walking the whole pin history costs more than a missed old change list is worth.

10. Advisory: A failed first report can mark unseen notes as shown.
    Raise: Functional  
    Case: normal use - The network is unavailable when the agent runs `forge next` while the upgrade waits to merge.  
    The planned helper writes the marker before returning its lines ([plan](/plans/FORGE-RELNOTES-1.md:260)), but `next` builds the rest of its report before printing those lines ([nextstep.py](/src/forge/nextstep.py:154)). For a ready fix, that report can attempt a fetch and fail ([nextstep.py](/src/forge/nextstep.py:1117), [repo.py](/src/forge/repo.py:688)). A retry then finds the marker already advanced, although the notes were never printed.  
    Gain 3, Work 3, Harm 3
   Disposition: cut - once() now writes nothing and next marks the version shown only after its final print, so a failed report marks nothing (Done-when 3 details; unreadable-notes case checks it).

11. Advisory: The unreadable-notes test cannot reach the planned `forge next` call as written.
    Raise: Test  
    The test puts invalid UTF-8 in the fake release before the upgrade ([plan](/plans/FORGE-RELNOTES-1.md:269)). Upgrade first runs that release’s `sync` ([upgrade.py](/src/forge/upgrade.py:250)); the planned guide renderer reads those same notes during sync ([sync.py](/src/forge/sync.py:434)). The upgrade fails before the test can check that `next` continues.  
    Gain 3, Work 2, Harm 2
   Disposition: cut - the unreadable-notes case now breaks the installed release's notes file after the upgrade finishes, so it reaches forge next.

## Round 3

12. Blocking: The new release check cannot start on this Mac.
    Raise: Functional  
    Case: normal use - A maintainer cuts a release from a Mac where Forge was installed with uv and no `python` command is on PATH.  
    The new pre-tag step requires `python` ([plan](/plans/FORGE-RELNOTES-1.md:174)), but this checkout’s environment has no `python` command. Forge’s supported installation lets uv supply Python ([README](/README.md:224)). The planned test uses `sys.executable` ([plan](/plans/FORGE-RELNOTES-1.md:210)), so it would pass without exercising the release command.  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted on 23 Nov 2026: the builder starts the release check with uv run --frozen --python 3.11 python instead of python; advisory 13 stays for the builders; no plan edit

13. Advisory: The worktree lookup conflicts with the module’s dependency rule.
    Raise: Plan gap  
    The plan permits `release_notes.py` to use only the standard library, `forge.__version__`, and `repo` ([plan](/plans/FORGE-RELNOTES-1.md:137)), but requires it to call `story.worktrees` ([plan](/plans/FORGE-RELNOTES-1.md:263)), which belongs to [story.py](/src/forge/story.py:801). A builder must choose which instruction to break.  
    Gain 3, Work 1, Harm 1
   Disposition: keep - below the bar (follow-up)
