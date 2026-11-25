# Finished work is cleaned up every time, and leftover work is listed with one next step

3 parts · Risks: removes folders of merged or closed work · New moving parts: none

## What changes for you

- When `forge next`, `forge start` or `forge land` runs, Forge removes the folder and local branch of every finished item on this machine. An item is finished when its pull request is merged, wherever the merge happened: on this machine, on another machine or on GitHub. When it removed any, Forge prints one line with how many. The folder the command runs in is left for the next run.
- Forge never removes a folder that has uncommitted files, or local commits that its pull request does not have. The one exception, as in `forge doctor --fix` today, is a lockfile change that running the tests made.
- A folder whose pull request was closed without a merge is removed only when its branch is still on GitHub, so the work can come back.
- The session-start hook stays fast and does not ask GitHub. It already tells the agent to run `forge next`, and that run does the cleanup.
- `forge next` shows every item that is not merged and not moving, in one block. Each item gets one next step: land it, or, for a fix, drop it with a reason. This covers an item with no pull request, a pull request closed without a merge, and a builder that stopped before it finished.
- `forge land` with no item lands every open item. That now includes items whose builder stopped before it finished. Forge merges only where the repo lets the agent merge. At the end, it shows one list of the decisions that are yours (a round limit, an approval).
- A new client repo and an existing client repo both get this when they upgrade. Nothing in the repo needs to change. A repo still pinned to an older release gets no cleanup until it upgrades.

## Why

Forge removes a finished folder only when `forge merge` runs on the same machine. A merge made on another machine, or by a person on GitHub, leaves the folder behind. `forge doctor --fix` can remove these folders, but only when someone runs it. At one client, about 115 local folders piled up. Some had merged pull requests, some had pull requests closed without a merge, and some never had a pull request. On one machine, 8 of 10 leftover folders belonged to pull requests that were already merged. `forge land --all` also leaves out items whose builder stopped, so those items never reach a merge.

## Done when

1. **After `forge next`, `forge start` or `forge land`, the folder and local branch of each merged item with no uncommitted files (other than a lockfile change from tests) and no extra local commits is gone, except the folder the command runs in, and one line says how many Forge removed when it removed any.**
2. **A folder whose pull request was closed without a merge is removed only when its branch is on GitHub. A folder with uncommitted files (other than a lockfile change from tests), or with local commits its pull request does not have, is never removed.**
3. **`forge next` lists every item that is not merged and not moving in one block, with one next step for each.**
4. **In a repo where the agent merges, `forge land` with no item merges every open item, including items whose builder stopped, and ends with one list of the owner's decisions.**

## Risks

Risks: removes folders of merged or closed work. Forge removes a folder only when its work is on GitHub (a merged pull request, or a closed pull request whose branch is still there) and the folder has no uncommitted files and no extra local commits. `forge doctor --fix` already uses the same check.

## For the builders

### Done-when details

1. Reuse the check that `forge doctor --fix` uses today (`src/forge/doctor.py` `_finished`, with `task.worktree_files`): the local branch head must equal a merged pull request's head (this is the "no extra local commits" rule, the same as `merge.py`'s advanced check), there is no open pull request for the branch, and `worktree_files` is empty. Move the check and the removal loop (doctor.py, near `finished = _finished(top, main)`) into one function, `doctor.tidy_finished(top) -> int`. The `uv.lock` exception in `worktree_files` stays: it is the owner-approved FORGE-DOCTORFIX-1 rule (tests change the lockfile). `forge doctor --fix` and the three commands call it. The other commands print only `Removed <n> finished folders.` when n > 0. Doctor keeps its per-folder lines.
   Speed: today `_finished` makes one `gh pr list` call per folder. With 115 folders that is 115 calls. Get every pull request for the local `story/`, `task/`, `fix/` and `forge/` branches in one `gh pr list --state all` request (or a few pages of it), with no cache: a cached "closed" can hide a reopened pull request. One request per command is about one second. Without `gh`, or when GitHub fails, remove nothing and print nothing. A failure here never stops the command. Run the cleanup only when the running Forge is the repo's pinned release (`forge next` does not switch to the pinned release, see `cli.py`), so a repo on an older release gets nothing until it upgrades.
   Never remove the main checkout, the folder that the command runs in, a folder with a live run (`machine.entries()` / `board.active_runs`), or a folder with `.gitmodules`.
   Tests (new repo, one test per rule): a pull request merged on GitHub with no local `forge merge` -> `forge next` removes the folder and branch and prints the count, and `forge land` with no item does the same; a folder with an uncommitted file is kept. Amend `tests/test_doctor_fix.py`, which stubs the per-branch GitHub request this part replaces.
2. Closed without a merge: remove the folder only when `git ls-remote --heads origin <branch>` returns the same head (one `ls-remote` call for all branches). Otherwise keep it, and done-when 3 lists it. Doctor's current check removes these without the remote check, so this change also makes doctor safer. Test: a closed pull request whose remote branch was deleted -> the folder stays and `forge next` lists it.
3. `nextstep.py` is at 1,197 lines (the ceiling is 1,200). Put the leftover block in `doctor.py` and have `nextstep.py` call it in one or two lines. "Not moving" means: no live run, not in close or ready, and one of: no pull request and no commit for 7 days (reuse `doctor._unbuilt`'s rule, now for every branch kind); a pull request closed without a merge that done-when 2 kept; or status working/started with no live builder (the interrupted check that `nextstep.py` already makes for one item). Each row: the item's title, why it is stuck in plain words, and one `Next:` line: `forge land <item>`, or `forge fix drop <item> --because "<reason>"` for a fix. A story part gets only `forge land <part>`: Forge has no command that drops one part. Test: one stalled fix with no pull request -> the block lists it with `forge land <item>`.
4. `land.py`: no item and no `--all` now means `--all`. Remove the `one_or_all` refusal for that case and keep it for "both". In `_queue`, an item whose builder is not done and has no live run is no longer "Left out": it runs through the single-item land path, which already builds when nothing is built. Items with a live run stay left out. The `needs` decisions print once, together, at the end of the run; the children's relayed output does not repeat them (test with two items that stop for owner decisions). Human-merge repos keep stopping at Ready with the pull request link. Test: one fix in close and one fix whose builder stopped -> `forge land` with no item merges both, using a fake worker. Amend `tests/test_queue_land_all.py`, which expects bare `forge land` to refuse and unfinished builders to be left out.
   Update `src/forge/templates/skill.md` in the same part: `forge land` with no item lands everything. (TIDY updates the guide line about finished folders.)
   New client repo: gets the rules from the release. Existing client repo: gets them on upgrade with no file change. No upgrade test is needed, because no record changes.

Related stories: FORGE-LAND-1 (done) made `forge land`; this story widens its no-item run. FORGE-DOCTORFIX-1 (done) made `forge doctor --fix` remove finished folders; this story moves that removal into a shared function and adds the remote-branch check.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| TIDY | Finished folders clean themselves up | One shared removal used by doctor, next, start and land, with one GitHub request | 1, 2 | src/forge/doctor.py, src/forge/nextstep.py, src/forge/intake.py, src/forge/land.py, src/forge/templates/skill.md | tests/test_tidy_finished_folders.py, tests/test_doctor_fix.py | | no | |
| LEFTOVERS | Stuck items listed with one next step | The forge next block for items that are not merged and not moving | 3 | src/forge/doctor.py, src/forge/nextstep.py | tests/test_next_lists_stuck_items.py | TIDY | no | |
| SWEEP | Land with no item lands everything | forge land with no item, including stopped builders, with one decision list at the end | 4 | src/forge/land.py, src/forge/templates/skill.md | tests/test_land_sweeps_all_items.py, tests/test_queue_land_all.py | TIDY | no | |

New moving parts: none

## Notes

- Owner choices, 25 Nov 2026: removal on every command, no new command; leftovers listed with land or drop; `forge land` sweeps everything.
- The owner chose cleanup in the session-start hook too. The hook is offline on purpose (`nextstep.context_hook`: no GitHub). The plan keeps it offline, because the hook already sends the agent to `forge next`, which does the cleanup. This is stated in "What changes for you" so that the approval covers it.
