# Hold a story for later, bring it back, and drop plans safely

3 parts · Risks: a held story's open pull requests are closed until it is brought back · New moving parts: none

## What changes for you

- You can put a story aside with `forge story drop <KEY> --later`. It works for a plan waiting for approval, an approved plan with nothing started, and a story with started parts that are not merged. Forge keeps every branch and the plan, closes the open pull requests of the story's parts so their files are free for other work, and records "held". (Source: owner request of 28 Nov 2026; issues 51 and 54)
- A held story never starts by itself. The background runner starts none of its parts and lands none of its started parts, `forge close` and `forge merge` stop for them, approving a held plan does not release it, and `forge next` does not offer them or list them as conflicts or waiting work. (Source: owner request of 28 Nov 2026; issues 51 and 54)
- `forge next` shows each held story in one block, in plain words, with the step that releases it: `forge story drop <KEY> --undo`. (Source: owner request of 28 Nov 2026)
- `forge story drop <KEY> --undo` brings a held or dropped story back as it was (planning, waiting for approval or approved), reopens the pull requests that the drop closed, brings back the checkouts of its started parts, and lets its parts start again. If another story took the files in the meantime, `--undo` refuses with one line. A drop made by an older release saved no pull request numbers, so `--undo` reopens nothing and prints the pull requests to reopen by hand. The same step replaces the old way of undoing a drop, which was to revert a commit by hand. (Source: owner request of 28 Nov 2026; mirrors `forge fix drop --undo`)
- A plan waiting for approval can now be dropped. Today Forge refuses it. (Source: issue 53)
- When you drop an approved plan with `--because`, Forge still drops it, because it is easy to undo. It now says in one line that the approval is dropped too, and that `--undo` brings it back, and it points to `--later` for putting the story aside. (Source: planner's choice, in place of a refusal; confirm)
- Fixes already have drop and `--undo`, and the runner never starts a dropped fix. Fixes get nothing new. (Source: planner's choice; confirm)
- A new client repo and an existing client repo both get this when they upgrade, with no file change. Both get the new lines in Forge's guide after `forge sync`. A story that an older release dropped can be brought back with `--undo` too. A repo still pinned to an older release gets nothing until it upgrades. (Source: planner's choice; confirm)

## Why

At one client, an approved story started at once and the owner had no way to wait for the next release. A story with started parts could not be put aside, so its parts kept showing up as conflicts. `forge story drop` dropped approved plans without a word, yet refused a plan that was only waiting for approval.

## Done when

1. **After `forge story drop <KEY> --later`, the background runner starts no part of that story, and `forge next` never offers its parts, however long the story stays held.**
2. **`forge next` lists each held story in one plain block with `Next: forge story drop <KEY> --undo`, and shows none of its parts as conflicts or waiting work.**
3. **`--later` works on a story with started parts that are not merged: every branch stays, the open pull requests of its parts close, and no part can start, land, close or merge (a close already running opens no pull request), and approving the held plan does not release it.**
4. **`forge story drop <KEY> --undo` brings the story back as it was and shows it on the board again, reopens the pull requests the drop closed, restores its started parts so the runner resumes them, and refuses with one line when other work took their files; holding twice keeps the first saved state.**
5. **A plan waiting for approval can be dropped, and dropping an approved plan says in one line that its approval is dropped and that `--undo` brings it back.**

## Risks

Risks: closed pull requests. `--later` closes the open pull requests of the story's parts, as a plain drop does today, and `--undo` reopens them. Their branches and comments stay the whole time. A part's builder that is still running when the story is held stops at its next step, as it does for a dropped story. Older drops cannot reopen their pull requests by themselves; `--undo` lists them.

## For the builders

### Must fix: notes from the last cold read (round 2)

The owner accepted the plan with these as must-fix items. Each part's builder fixes the ones it owns and tests them; its review checks them. Full cases: `plans/FORGE-STORYHOLD-1.read.md`, Round 2.

- **12, HOLD/RESTORE:** HOLD's change to the approved-story test must not need `--undo`; move that test change to RESTORE.
- **13, HOLD:** refusing an approval of a held plan must leave the checkout clean (no uncommitted story record), so `--undo` still works.
- **14, RESTORE:** a restored story must be started by the runner even when its approval is older than the runner's install time (for example, record the restore time and let the runner use it).
- **16, RESTORE:** the board rule must keep showing a story's remaining parts as held after an earlier part merged.
- **17, HOLD:** close that already has an open pull request must not record Ready for a held story; test that path.
- **18, RESTORE:** the overlap check on undo must also see open fixes that use the same files.
- **19, RESTORE:** the by-hand reopen list for old records must match `task/<KEY>-<part>` exactly, never a longer story key.
- **21, RESTORE:** undo after an earlier part merged must skip the merged part (its branch is gone) and restore only the held ones; test it.
- **22, HOLD:** `merge.py`'s wait-then-merge path must refuse a held story; add `src/forge/merge.py` to HOLD's Scope and test it.

Known issues (owner accepted, not fixed in this story): 15, a close that finishes its review in the seconds while a hold is closing pull requests can leave one request open (workaround: run the hold again); 20, approving from a stale checkout while a teammate holds the plan elsewhere can leave the two story branches different (workaround: fetch, then run the hold again).

### Done-when details

1. Hold is the existing dropped state plus a marker, so every check that already hides a dropped story keeps working (`nextstep.py` hides it at the end of the story scan, `task.py` REFUSALS `dropped`, `board.py`, `land.py`, `machine.py`, `_has_approved_unstarted`). `forge story drop` lives in `src/forge/intake.py` `story_drop`, not `story.py` (`story.py` is 1,200 lines and `nextstep.py` 1,198; the ceiling is 1,200, so add nothing to them beyond one or two call lines). New option: `--later` (the reason is optional with it; default "The owner wants it later"), stored as `drop.later = true`. One gap: `runner._story_eligible` does not look at the story status, so the runner would still land the started parts of a dropped story. Return False there when the record is `dropped`. Test (the pattern in `tests/test_runner_moves_approved_work_to_merge.py`): start a part, hold the story, run the runner: no `forge land` and no `forge task start` runs for it (this test fails without the runner change, because `forge next` already hides dropped stories); `forge next` has no `task start` line for it.
2. New helper `held_block(top) -> list[str]` in `src/forge/intake.py`, called from `nextstep._report` in one line. It reads each story record (use `story.plan_ref` and `story.show`, as `story_drop` does) and prints, per held story, `<title> is held for later.` and `Next: forge story drop <KEY> --undo`. A story dropped with `--because` and no `--later` is not listed (the owner dropped it). Test: hold a story whose part is started; `forge next` shows the block and no conflict line naming the part.
3. `--later` skips the "has started parts" refusal (it fires only when a part's record is on the default branch, that is, a part merged; it cannot be reproduced for parts that are only started, so the builder first writes a test with started unmerged parts and records whether plain drop already works there). With merged parts, `--later` still holds the story; the merged parts stay merged. Plain drop keeps that refusal. PR closing is the loop that exists in `story_drop`. Stops: `src/forge/close.py` checks the story only when close starts, so it re-checks the story record (`task.require_active`) right before it opens the pull request and before it merges, and refuses with the `dropped` line; `forge merge` does the same. `src/forge/approval.py` refuses to approve a plan whose record is `dropped`, with `Next: forge story drop <KEY> --undo`. Repeating a hold on a dropped story changes nothing: it keeps the first `drop` record (status and pull request numbers), prints that the story is already held, and exits 0. Tests: a hold while close runs opens no pull request; the approval hook on a held plan refuses and leaves it dropped; a second `--later` keeps the first record. Test with a fake GitHub as in `tests/test_story_drop_frees_parked_parts.py`: parts' pull requests close; branches exist on the remote; `forge task start` and `forge close` on a part refuse with "is dropped".
4. Mirror `task.fix_drop --undo`: save `drop.status` (the earlier status) and `drop.pull_requests` (numbers it closed) when dropping; on `--undo`, refuse unless the story is dropped, restore the status, reopen those pull requests that are still closed (`close._gh(... "pr", "reopen" ...)`), add a restore step, commit "Restore the plan", push. A drop made by an older release has no `drop.status` or pull request numbers: restore to `approved` when the record has an approval hash, else `planning`, reopen nothing, and print `Reopen these pull requests by hand:` with the open-or-closed `task/<KEY>-*` and story pull requests that GitHub lists for those branches. Before restoring, run the same file-overlap check that `forge task start` runs (`task.can_start` with the part's Scope and the busy set, as in `nextstep`) for each started part; when another item took its files, refuse with that one line and change nothing. Cleanup can remove a held part's clean checkout and branch, so `--undo` recreates each started part's checkout from its remote branch (`git worktree add -b task/<KEY>-<ID> ... origin/task/<KEY>-<ID>`), as `fix drop --undo` does, which lets the runner resume it. `src/forge/board.py` (line 268) hides a story when any copy says dropped; make it use the newest record (the default branch's state, else the latest story branch's) so a stale checkout cannot hide a restored story. `--undo` and `--because`/`--later` exclude each other, with one refusal line, as in `fix_drop`. Tests: hold then `--undo` on an approved story with a started part: `forge next` offers its parts, the pull request is open, the part's checkout exists and the board shows the story; a stale dropped copy on another checkout does not hide it; an overlapping started item makes `--undo` refuse; an older-release drop prints the by-hand line.
5. Allow the status `read` in the refusal list in `story_drop` (today only `planning`, `approved`, `dropped`). For an approved plan with `--because`, print the extra line after "Dropped plan <KEY>." Update `tests/test_approved_story_drop.py` (it drops an approved story and reverts by hand; add the line check and replace the hand revert with `--undo`). Test: a story in `read` drops; an approved one prints the line.

RESTORE does the guide update. Update `src/forge/templates/skill.md` in the same change, as the review rules require: the "Make it a fix" row (it names `story drop`), a new "Do it later" row for a story (`forge story drop <KEY> --later`, release with `--undo`), and the commands table entry (`listing` in the `story drop` command in `intake.py`). Then run `uv run --frozen forge sync` and commit the synced copies (`.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`) and `docs/commands.md`, which sync also changes (`tests/test_split_page.py` fails without it). `brief.md` needs no change: workers never hold stories. The command count stays at 26, so `test_rules.py::test_5_forge_stays_small` is unaffected. Before a round ends, run the two cheap checks in `AGENTS.md`.

Upgrade: no record format breaks. The marker `drop.later` and the saved `drop.status` are new keys on a record that older Forge ignores, and the restore rule in item 4 covers older drops. No new upgrade test; `tests/test_upgrade_to_installed_release.py` stays as it is.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| HOLD | Hold a story and stop its parts | `--later` and the drop of a `read` plan with the approval line; the runner, close, merge and approval stop for a held story; a repeated hold keeps the first record | 1, 3, 5 | src/forge/intake.py, src/forge/runner.py, src/forge/close.py, src/forge/approval.py | tests/test_story_hold.py, tests/test_approved_story_drop.py | | no | |
| RESTORE | Bring a held story back | `--undo` with the saved state, the overlap check, restored part checkouts, the board fix and the guide update | 4 | src/forge/intake.py, src/forge/board.py, src/forge/templates/skill.md, .claude/skills/forge/SKILL.md, .codex/skills/forge/SKILL.md, docs/commands.md | tests/test_story_restore.py | HOLD | no | |
| HELD | Held stories shown by forge next | The held block with the release step, in plain words | 2 | src/forge/intake.py, src/forge/nextstep.py | tests/test_next_shows_held_stories.py | RESTORE | no | |

New moving parts: none

## Notes

- Owner request of 28 Nov 2026: "This is needed in next release as other client has need it" (v1.2.51). Source issues: 51 (hold), 53 (drop message and `read` plans), 54 (put aside started parts).
- Both new test files start with `STORY = "FORGE-STORYHOLD-1"`, run the `forge` command only and never import forge, and have one `test_<n>_...` function per Done-when number they cover.
- Open question for the owner: should dropping an approved plan refuse (naming `--later`) instead of printing a line? The plan prints the line, because a drop is now easy to undo and the "Make it a fix" step of the guide drops approved plans on purpose.
