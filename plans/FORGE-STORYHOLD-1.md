# Hold a story for later, bring it back, and drop plans safely

2 parts · Risks: a held story's open pull requests are closed until it is brought back · New moving parts: none

## What changes for you

- You can put a story aside with `forge story drop <KEY> --later`. It works for a plan waiting for approval, an approved plan with nothing started, and a story with started parts that are not merged. Forge keeps every branch and the plan, closes the open pull requests of the story's parts so their files are free for other work, and records "held". (Source: owner request of 28 Nov 2026; issues 51 and 54)
- A held story never starts by itself. The background runner starts none of its parts, and `forge next` does not offer them or list them as conflicts or waiting work. (Source: owner request of 28 Nov 2026; issues 51 and 54)
- `forge next` shows each held story in one block, in plain words, with the step that releases it: `forge story drop <KEY> --undo`. (Source: owner request of 28 Nov 2026)
- `forge story drop <KEY> --undo` brings a held or dropped story back as it was (planning, waiting for approval or approved), reopens the pull requests that the drop closed, and lets its parts start again. The same step replaces the old way of undoing a drop, which was to revert a commit by hand. (Source: owner request of 28 Nov 2026; mirrors `forge fix drop --undo`)
- A plan waiting for approval can now be dropped. Today Forge refuses it. (Source: issue 53)
- When you drop an approved plan with `--because`, Forge still drops it, because it is easy to undo. It now says in one line that the approval is dropped too, and that `--undo` brings it back, and it points to `--later` for putting the story aside. (Source: planner's choice, in place of a refusal; confirm)
- Fixes already have drop and `--undo`, and the runner never starts a dropped fix. Fixes get nothing new. (Source: planner's choice; confirm)
- A new client repo and an existing client repo both get this when they upgrade, with no file change. Both get the new lines in Forge's guide after `forge sync`. A story that an older release dropped can be brought back with `--undo` too. A repo still pinned to an older release gets nothing until it upgrades. (Source: planner's choice; confirm)

## Why

At one client, an approved story started at once and the owner had no way to wait for the next release. A story with started parts could not be put aside, so its parts kept showing up as conflicts. `forge story drop` dropped approved plans without a word, yet refused a plan that was only waiting for approval.

## Done when

1. **After `forge story drop <KEY> --later`, the background runner starts no part of that story, and `forge next` never offers its parts, however long the story stays held.**
2. **`forge next` lists each held story in one plain block with `Next: forge story drop <KEY> --undo`, and shows none of its parts as conflicts or waiting work.**
3. **`--later` works on a story with started parts that are not merged: every branch stays, the open pull requests of its parts close, and its parts cannot start or close.**
4. **`forge story drop <KEY> --undo` brings the story back as it was, reopens the pull requests the drop closed, and its parts can start again.**
5. **A plan waiting for approval can be dropped, and dropping an approved plan says in one line that its approval is dropped and that `--undo` brings it back.**

## Risks

Risks: closed pull requests. `--later` closes the open pull requests of the story's parts, as a plain drop does today, and `--undo` reopens them. Their branches and comments stay the whole time. A part's builder that is still running when the story is held stops at its next step, as it does for a dropped story.

## For the builders

### Done-when details

1. Hold is the existing dropped state plus a marker, so every check that already hides a dropped story keeps working (`nextstep.py` hides it at the end of the story scan, `task.py` REFUSALS `dropped`, `board.py`, `land.py`, `machine.py`, `_has_approved_unstarted`). `forge story drop` lives in `src/forge/intake.py` `story_drop`, not `story.py` (`story.py` is 1,200 lines and `nextstep.py` 1,198; the ceiling is 1,200, so add nothing to them beyond one or two call lines). New option: `--later` (the reason is optional with it; default "The owner wants it later"), stored as `drop.later = true`. One gap: `runner._story_eligible` does not look at the story status, so the runner would still land the started parts of a dropped story. Return False there when the record is `dropped`. Test: approve a story, hold it, run the runner (the pattern in `tests/test_runner_moves_approved_work_to_merge.py`): no `forge task start` runs; `forge next` has no `task start` line for it.
2. New helper `held_block(top) -> list[str]` in `src/forge/intake.py`, called from `nextstep._report` in one line. It reads each story record (use `story.plan_ref` and `story.show`, as `story_drop` does) and prints, per held story, `<title> is held for later.` and `Next: forge story drop <KEY> --undo`. A story dropped with `--because` and no `--later` is not listed (the owner dropped it). Test: hold a story whose part is started; `forge next` shows the block and no conflict line naming the part.
3. `--later` skips the "has started parts" refusal (it fires only when a part's record is on the default branch, that is, a part merged; it cannot be reproduced for parts that are only started, so the builder first writes a test with started unmerged parts and records whether plain drop already works there). With merged parts, `--later` still holds the story; the merged parts stay merged. Plain drop keeps that refusal. PR closing is the loop that exists in `story_drop`. Test with a fake GitHub as in `tests/test_story_drop_frees_parked_parts.py`: parts' pull requests close; branches exist on the remote; `forge task start` and `forge close` on a part refuse with "is dropped".
4. Mirror `task.fix_drop --undo`: save `drop.status` (the earlier status) and `drop.pull_requests` (numbers it closed) when dropping; on `--undo`, refuse unless the story is dropped, restore the status, reopen those pull requests that are still closed (`close._gh(... "pr", "reopen" ...)`), add a restore step, commit "Restore the plan", push. A drop made by an older release has no `drop.status`: restore to `approved` when the record has an approval hash, else `planning`. `--undo` and `--because`/`--later` exclude each other, with one refusal line, as in `fix_drop`. Test: hold then `--undo` on an approved story; `forge next` offers its part again and the pull request is open.
5. Allow the status `read` in the refusal list in `story_drop` (today only `planning`, `approved`, `dropped`). For an approved plan with `--because`, print the extra line after "Dropped plan <KEY>." Update `tests/test_approved_story_drop.py` (it drops an approved story and reverts by hand; add the line check and replace the hand revert with `--undo`). Test: a story in `read` drops; an approved one prints the line.

Also update `src/forge/templates/skill.md` in the same change, as the review rules require: the "Make it a fix" row (it names `story drop`), a new "Do it later" row for a story (`forge story drop <KEY> --later`, release with `--undo`), and the commands table entry (`listing` in the `story drop` command in `intake.py`). Then run `uv run --frozen forge sync` and commit the synced copies (`.claude/skills/forge/SKILL.md` and the Codex copy). `brief.md` needs no change: workers never hold stories. The command count stays at 26, so `test_rules.py::test_5_forge_stays_small` is unaffected. Before a round ends, run the two cheap checks in `AGENTS.md`.

Upgrade: no record format breaks. The marker `drop.later` and the saved `drop.status` are new keys on a record that older Forge ignores, and the restore rule in item 4 covers older drops. No new upgrade test; `tests/test_upgrade_to_installed_release.py` stays as it is.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| HOLD | Hold, restore and safe drop | `--later` and `--undo` on `forge story drop`, drop of a `read` plan, the approval line, the runner skip | 1, 3, 4, 5 | src/forge/intake.py, src/forge/runner.py, src/forge/templates/skill.md, .claude/skills/forge/SKILL.md, .codex/skills/forge/SKILL.md | tests/test_story_hold.py, tests/test_approved_story_drop.py | | no | |
| HELD | Held stories shown by forge next | The held block with the release step, in plain words | 2 | src/forge/intake.py, src/forge/nextstep.py | tests/test_next_shows_held_stories.py | HOLD | no | |

New moving parts: none

## Notes

- Owner request of 28 Nov 2026: "This is needed in next release as other client has need it" (v1.2.51). Source issues: 51 (hold), 53 (drop message and `read` plans), 54 (put aside started parts).
- Both new test files start with `STORY = "FORGE-STORYHOLD-1"`, run the `forge` command only and never import forge, and have one `test_<n>_...` function per Done-when number they cover.
- Open question for the owner: should dropping an approved plan refuse (naming `--later`) instead of printing a line? The plan prints the line, because a drop is now easy to undo and the "Make it a fix" step of the guide drops approved plans on purpose.
