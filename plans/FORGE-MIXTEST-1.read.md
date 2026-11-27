---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-27T09:21:12.616562+00:00
seconds: 435.256
read_hash: f3eb09a75b810379f985e8d4f0b494bd2ce31e30
round: 2
passed: no
doc_seen: f3eb09a75b810379f985e8d4f0b494bd2ce31e30
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 1264f8aa72674d8a54e4d98bdec8a95f437a288a
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21c39-cb5d-7a13-9178-e47d07ae1105
session:
loop_choice: more
loop_reason: One more round: fix notes 8 and 9, and add the owner's 27 Nov request that the release full-suite run goes to GitHub
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

1. **Blocking: Not done: A wide change can pass without any tests running.**  
   Raise: Not done.  
   Case: normal use - The default branch changes a root test input while a pull request is open. If GitHub allows the branches to merge without updating the pull request branch, [close.py](/src/forge/close.py:755) leaves it unmerged. [fasttest.py](/src/forge/fasttest.py:398) then sees the default branch’s input as a change and selects the wide path. GitHub tests a merged checkout, where that input is unchanged, so it can select narrow and report a green skipped `tests` check. Close accepts that check after skipping local tests.  
   Gain 5, Work 3, Harm 3

   Disposition: cut Close now measures the change from the branch's merge-base with the default branch, the same changes the GitHub job sees, so a root input that only reached the default branch no longer makes a change wide; the Accepted limit text states the remaining rare case; a test covers it.

2. **Blocking: Functional: Grouped runs can pass when a named proof test never ran.**  
   Raise: Functional.  
   Case: normal use - A pytest filter excludes the test named in a task’s proof list while other tests run. Local close currently refuses a missing named result, but [proof.py](/src/forge/proof.py:224) does not require a match when multiple groups run. The planned wide path can therefore report green despite the named test never running, contrary to the [worker brief](/src/forge/templates/brief.md:712).  
   Adds work: verify named proof tests across groups; F 2 x H 2 = 4; 2 x C = 4.  
   Gain 4, Work 2, Harm 3

   Disposition: keep The `ci` place already behaves this way: `proof.check` counts a missing named result only when FORGE_GROUPS is 1, and mixed's wide path is the same run as `ci`. It needs a pytest filter that drops a named test, so F 1 x H 2 = 2 is below 2 x C = 4 (a per-group proof check is more than 150 lines or a new step). Noted in Notes.

3. **Blocking: Not done: A wide test-only change can run in one GitHub group.**  
   Raise: Not done.  
   Case: normal use - A change edits more than a third of a suite’s independent Python test files. [review-tests.py](/src/forge/templates/review-tests.py:154) marks independent test-only changes for one group regardless of their size, and [prcheck.py](/src/forge/prcheck.py:89) uses that output for its matrix. The planned test checks that the matrix lists groups, so it can pass while the wide run uses only one.  
   Gain 4, Work 2, Harm 3

   Disposition: cut review-tests.py now sets `one_group = one_group and not wide`, so a wide test-only change runs every group; a test checks `one-group=false`.

4. **Blocking: Not done: The wide calculation counts files outside the configured suite.**  
   Raise: Not done.  
   Case: normal use - A repository runs `pytest tests` and also keeps example tests elsewhere. [fasttest.py](/src/forge/fasttest.py:400) counts all tracked Python test files. With the existing [12-suite-file and 48-example-file fixture](/tests/test_selected_tests_choose_groups.py:45), a change selecting all 12 suite files is calculated as 12 of 60 and remains on the laptop.  
   Gain 4, Work 2, Harm 3

   Disposition: keep Not worth the code: a repo with many test files outside the suite roots would only keep a wide change on the laptop, which is today's `local` behaviour and runs every selected test (F 1 x H 1 = 1 is below 2 x C = 4; fixing it needs the suite-root parsing that `small_change` has). Noted in Notes.

5. **Blocking: Functional: A non-pytest repository without `fast_test` can be sent to GitHub.**  
   Raise: Functional.  
   Case: normal use - A Node repository uses its test script as `test` and leaves `fast_test` unset. A dependency change to `package-lock.json` makes [related()](/src/forge/fasttest.py:415) report a shared input, so the proposed calculation sends the script to GitHub. Yet [close_tests()](/src/forge/fasttest.py:299) does not use the pytest picker for that command, contrary to the plan’s stated limit.  
   Gain 3, Work 2, Harm 3

   Disposition: cut `fasttest.wide` now returns false unless `fast_test` is the pytest picker or empty, `test` is exactly one python part, and `repo.pytest_split` is true, so a Node repo with no `fast_test` never goes to GitHub; the Accepted limit text and a test cover it.

6. **Blocking: Functional: Closing a stacked wide change reports it tested without waiting.**  
   Raise: Functional.  
   Case: normal use - A task is stacked on a parent that has not merged. [close.py](/src/forge/close.py:482) skips the check wait for that task and then returns success saying it is tested. The proposed wide path also skips local tests, so the message can appear while GitHub’s tests are missing or red.  
   Gain 4, Work 2, Harm 3

   Disposition: keep The stacked path returns before the Ready file is written (`close.py` lines 504 to 508), so nothing passes untested; close runs again after the parent merges, then `stacked_waiting` is false and the `tests` wait runs. Only the word "tested" in one message is off, and a `ci` task says the same today (F 1 x H 1 = 1 is below 2 x C = 2). Noted in Notes.

7. **Blocking: Unproven: Item 1 does not cover a repository configured for one group.**  
   Raise: Test.  
   Case: normal use - New repositories start with one group, as [the existing test](/tests/test_groups_pytest.py:139) shows. [prcheck.py](/src/forge/prcheck.py:418) currently combines the selector and tests into one job in that case. The planned tests use a grouped repository, so they can pass while a small change still starts the single GitHub test job.  
   Gain 3, Work 2, Harm 3

   Disposition: cut Mixed acts as `local` when `groups = 1` (`wide` returns false, `prcheck` builds the `local` workflow only for `mixed and groups > 1`), so no single GitHub test job starts for a small change; the Accepted limit text and the tests use `groups = 2` plus a one-group case.

## Round 2

8. **Blocking: Not done: One-group repositories can lose a required check when switching to mixed.**  
   Raise: Not done.  
   Case: normal use - A repository created with GitHub Actions keeps Forge’s default one group and requires `tests` in branch protection. [Init](/src/forge/init.py:204) sets one group, and [protect](/src/forge/init.py:259) requires the named checks. The amended [plan](/plans/FORGE-MIXTEST-1.md:40) gives this repository the local workflow, which [emits no `tests` check](/tests/test_testplace_workflow.py:113). The settings pull request cannot merge while that check remains required.  
   Gain 5, Work 2, Harm 3

9. **Advisory: Not done: The selector change also alters existing CI repositories.**  
   Raise: Not done.  
   Case: normal use - A CI repository with multiple groups edits more than a third of its independent test files. The current [selector](/src/forge/templates/review-tests.py:154) chooses one group, but the amended [plan](/plans/FORGE-MIXTEST-1.md:41) applies `one_group = one_group and not wide` without limiting it to mixed mode. The planned workflow comparison can pass while that CI repository starts every group.  
   Gain 3, Work 2, Harm 3

10. **Advisory: Functional: Switching from CI to mixed removes the existing nightly full run.**  
    Raise: Functional.  
    Case: normal use - A CI repository relies on Forge’s generated nightly full suite and has no separate full-suite workflow. The amended plan keeps `full_run` limited to CI mode; [prcheck.py](/src/forge/prcheck.py:306) consequently removes the schedule after the settings fix merges. The full run then needs to be started manually, even though [test selection](/src/forge/fasttest.py:850) still says the nightly run covers missed tests.  
    Adds work: retain the existing nightly run after switching; F 3 x H 2 = 6; 2 x C = 6.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)
