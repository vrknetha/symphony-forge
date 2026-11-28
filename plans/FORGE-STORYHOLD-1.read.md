---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-28T01:13:23.552986+00:00
seconds: 600.619
read_hash: a0db4a06a26b8ab86a602ee0660bd0903881ba84
round: 1
passed: no
doc_seen: a0db4a06a26b8ab86a602ee0660bd0903881ba84
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21fad-ad4a-7d51-8190-522e1817507f
session:
loop_choice:
loop_reason:
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

1. Blocking: Not done: item 3 — a close already in progress can open a pull request after the story is held.
   Raise: Not done
   Case: normal use - The owner holds a part while its review or tests are running, before it has a pull request. [close.py](/src/forge/close.py:658) checks the story only when close starts, then can [open the pull request](/src/forge/close.py:985) after the hold. The runner change only prevents new runs.
   Gain 4, Work 3, Harm 3
   Disposition: cut - Done-when 3 and the details now make close re-check the story before it opens a pull request and before it merges, and `forge merge` stops too.

2. Blocking: Not done: item 1 — an approval can release a held story without `--undo`.
   Raise: Not done
   Case: normal use - A plan is held while an approval reply is pending, and its checkout remains because it contains ignored local files. [approval.py](/src/forge/approval.py:100) still matches the held plan, then [sets its status to approved](/src/forge/approval.py:195), allowing the runner to start it.
   Gain 4, Work 3, Harm 3
   Disposition: cut - the approval hook now refuses to approve a held plan, with the `--undo` step; added to Done-when 3 and its test.

3. Blocking: Not done: item 4 — normal cleanup can leave restored parts outside the runner.
   Raise: Not done
   Case: normal use - The owner runs `forge next` while a started part is held, then restores the story. [Cleanup](/src/forge/doctor.py:130) can remove the closed part’s clean local checkout and branch. The planned undo recreates the story checkout only, while the [runner](/src/forge/runner.py:171) resumes started parts only from local checkouts.
   Gain 4, Work 3, Harm 3
   Disposition: cut - `--undo` now recreates each started part's checkout from its remote branch so the runner resumes it; added to Done-when 4 and its test.

4. Blocking: Not done: item 4 — older drops have no saved pull requests to reopen.
   Raise: Not done
   Case: normal use - An existing repo upgrades and restores a story dropped by an older release. The [current drop record](/src/forge/intake.py:284) saves no pull request numbers. The [plan’s fallback](/plans/FORGE-STORYHOLD-1.md:39) restores only the status, so it cannot reopen the requests that drop closed.
   Gain 3, Work 3, Harm 3
   Disposition: cut - an older drop has no pull request numbers: `--undo` reopens nothing and prints the pull requests to reopen by hand; stated in What changes and the details.

5. Blocking: Unproven: item 4 — repeating a drop can overwrite the information needed to undo it.
   Raise: Test
   Case: normal use - An owner retries a hold after an interrupted command. [story_drop](/src/forge/intake.py:271) accepts an already dropped story and replaces its drop record. Saving the current status and currently open requests again would save `dropped` and an empty list; the planned single-drop test would pass.
   Gain 3, Work 2, Harm 3
   Disposition: cut - a repeated hold keeps the first saved state and pull request list; added to Done-when 4 and given its own test.

6. Blocking: Restoring a story can resume two parts that use the same files.
   Raise: Functional
   Case: normal use - Another story starts work on the files freed by a hold, and the owner restores the first story before that work merges. [Task admission](/src/forge/task.py:543) checks overlap when a part starts, but the planned undo reactivates an already-started part without that check.
   Adds work: make restored parts wait for overlapping work; F 2 x H 2 = 4; 2 x C = 4
   Gain 3, Work 2, Harm 3
   Disposition: cut - `--undo` runs the same file-overlap check as `forge task start` for each started part and refuses with one line; added to Done-when 4 and its test.

7. Blocking: Not done: item 4 — a restored story can remain hidden on a teammate’s board.
   Raise: Not done
   Case: normal use - One machine keeps the held story checkout because it contains ignored files, and another machine restores it. Even after fetching the restore, [board.py](/src/forge/board.py:268) hides the story if **any** local or remote copy still says dropped. The stale local checkout therefore hides the restored story and its parts.
   Gain 3, Work 2, Harm 3
   Disposition: cut - the board now uses the newest record, not any copy, so a stale checkout cannot hide a restored story; `src/forge/board.py` joins RESTORE's scope.

8. Blocking: Unproven: item 1 — the runner test does not cover an already-started part.
   Raise: Test
   Case: normal use - The owner holds a story after a part has started. The [planned test](/plans/FORGE-STORYHOLD-1.md:36) checks only that no `task start` runs. It would pass without the runner fix because `forge next` already hides dropped stories, while the [runner separately selects started checkouts](/src/forge/runner.py:503) for `forge land`.
   Gain 3, Work 2, Harm 3
   Disposition: cut - the runner test now starts a part, holds the story and checks that no `forge land` runs; it fails without the runner change.

9. Blocking: The generated command page is outside the task’s scope.
   Raise: Plan gap
   Case: normal use - HOLD changes the command listing and runs sync as instructed. [sync.py](/src/forge/sync.py:740) also changes `docs/commands.md` in this repo, but [HOLD’s scope](/plans/FORGE-STORYHOLD-1.md:50) excludes it. Leaving the page out makes [its existing test](/tests/test_split_page.py:20) fail.
   Gain 4, Work 1, Harm 2
   Disposition: cut - `docs/commands.md` is in RESTORE's scope, with the other synced copies.

10. Advisory: Give the shared production file one task owner.
    Raise: Plan gap
    [Both tasks](/plans/FORGE-STORYHOLD-1.md:50) own `intake.py`, and HELD adds its helper there after HOLD. The requested task rule gives a shared production file and its shared names to the first task; the later task owns its own files.
    Gain 3, Work 1, Harm 2
   Disposition: keep - below the bar (follow-up)

11. Advisory: Split: HOLD → hold and runner; restore and safe drop.
    Raise: Plan gap
    [HOLD](/plans/FORGE-STORYHOLD-1.md:50) covers four Done-when items. The requested planning check calls for a split when one task covers more than three.
    Gain 2, Work 1, Harm 1
   Disposition: keep - below the bar (live with)
