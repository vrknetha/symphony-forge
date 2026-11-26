---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-26T13:21:04.995277+00:00
seconds: 805.12
read_hash: 96110c348603236d850a6ecf6bba7e5f0b117c33
round: 2
passed: no
doc_seen: 96110c348603236d850a6ecf6bba7e5f0b117c33
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: a921304a2472b6d87a85165e85f339b1bce18c50
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a217d3-720e-7080-9989-1f8128bcbc7e
session:
loop_choice: more
loop_reason: Owner chose one more round for notes 16, 17, 18, 21
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

1. Blocking: Automatic work can erase a coordinator’s settings edit.  
   Raise: Data loss  
   Case: normal use - a coordinator starts a settings fix, then edits `forge.toml` before the fix’s Done-when names that file.  
   The plan starts a worker immediately. The documented settings flow has the coordinator make that edit, but [worker.py](/src/forge/worker.py:464) restores both staged and unstaged `forge.toml` changes when the fix has not yet named the file.  
   Adds work: protect coordinator edits during automatic builds; F 2 x H 3 = 6; 2 x C = 4  
   Gain 4, Work 2, Harm 5
   Disposition: cut The plan says a settings fix starts with `--done` naming `forge.toml`; then `task.settings_allowed` is true and `_restore_settings` leaves the coordinator's edit alone (guide text and the "Settings" bullet; no new code).

2. Blocking: Not done: item 5: stopping an item during its check wait does not stop its land process.  
   Raise: Functional  
   Case: normal use - the owner stops an item while its pull-request checks are running.  
   The plan records the stop but only prevents a *new* land run. The check wait is recorded outside the machine entries that [machine.stop](/src/forge/machine.py:640) stops; [checks.py](/src/forge/checks.py:141) keeps the existing process alive. It can continue to merge after the stop.  
   Gain 4, Work 2, Harm 3
   Disposition: cut `land` now checks `stops.stopped` at its start, each close round and before the merge, so `forge stop <item>` during a check wait lets no new round or merge happen (item 5, with a test that no `pr merge` follows).

3. Blocking: Not done: item 3: a check wait can prevent independent work from starting.  
   Raise: Functional  
   Case: normal use - a two-core machine has two ready fixes and the first waits for running checks.  
   The plan counts each entire `forge land` process against its one available place. The existing queue explicitly lends a place during running checks, as covered by [test_land_releases_check_wait_slots.py](/tests/test_land_releases_check_wait_slots.py:65). The proposed direct land calls do not use that handoff, so the second fix waits for the first check to finish.  
   Gain 4, Work 2, Harm 3
   Disposition: cut The runner no longer limits land runs; places are taken inside `land` (agent and test runs) and a check wait holds none, so a waiting check blocks no other fix.

4. Blocking: Not done: item 1: parallel fetch collisions permanently park ready work.  
   Raise: Functional  
   Case: normal use - two independent changes close together and fetch the same Git reference.  
   [land.py](/src/forge/land.py:660) already retries these lock collisions. The plan bypasses that queue and parks every nonzero land result; releasing the Git lock does not change the parked signature.  
   Gain 4, Work 2, Harm 3
   Disposition: cut A non-zero land exit that is not a "needs you" stop (git lock, short network problem, crash) is tried again twice, 10 s and 30 s later, as `land._queue` does, before it reaches `stops.ended`.

5. Blocking: Not done: item 1: a human merge can strand an already-stacked child.  
   Raise: Functional  
   Case: normal use - a child pull request targets its parent’s branch when the owner merges the parent on GitHub.  
   The planned poll only tidies the parent and retries the child. [close.py](/src/forge/close.py:694) then refuses until the child pull request is retargeted, requiring another owner action. The planned human-merge test does not require an already-stacked child.  
   Gain 4, Work 2, Harm 3
   Disposition: cut The runner sets `FORGE_RUNNER`, and `task.stack_base` then returns None, so the runner builds no stacked part; a waiting part starts after its base has merged (owner text already says this). A child a coordinator stacked earlier meets the existing `base_merged_by_hand` refusal, which is a normal stop with its own next step.

6. Blocking: Not done: item 5: a replacement runner can start a second land process for the same item.  
   Raise: Functional  
   Case: normal use - the runner is killed after a build finishes while its land child continues into close.  
   The planned live-run checks observe individual worker, review and check runs, not the whole land process. Between those steps, [land.py](/src/forge/land.py:104) can still be active while neither proposed check identifies it. This is the restart point the plan explicitly promises to handle.  
   Gain 4, Work 2, Harm 3
   Disposition: cut `land()` takes a per-item lock file for its whole run, which the system releases however the process ends; a replacement runner, a queue child or a hand-run land meets it and does not start a second land run for the item.

7. Blocking: Not done: item 4: runner-only stops are absent from the next-step report.  
   Raise: Functional  
   Case: normal use - on Windows, a worker kit is missing.  
   [worker.ready](/src/forge/worker.py:217) refuses before changing the item state. The plan stores the reason in `runner.json`, but leaves [nextstep.py](/src/forge/nextstep.py:1050) unchanged and specifies no path for it to read that reason. Windows has no pop-up, so the promised setup line is unavailable there.  
   Gain 4, Work 2, Harm 3
   Disposition: cut The Windows limit now says the stopped item stays in the next-step report with its usual next step, and running that step shows the reason; `nextstep.py` (at 1,200 lines) does not change.

8. Blocking: Not done: item 2: cleanup silently keeps a dirty folder.  
   Raise: Functional  
   Case: normal use - a person leaves local changes in an item folder before merging its pull request.  
   The plan expects `tidy_finished`’s report callback to name the folder. [doctor.py](/src/forge/doctor.py:228) instead skips a folder with local changes before calling that callback. The runner can finish without removing the folder or telling the owner why it remains.  
   Gain 3, Work 2, Harm 3
   Disposition: cut Done-when 2 now says the folder is removed when it holds no local changes; the runner leaves a dirty folder alone and says nothing, because it is a person's own data and nothing breaks.

9. Blocking: A story merged by a person remains unfinished on the board.  
   Raise: Functional  
   Case: normal use - the owner merges the final part on GitHub.  
   [merge.py](/src/forge/merge.py:190) writes the completion record only when Forge performs the merge. After a human merge, [nextstep.py](/src/forge/nextstep.py:672) still asks for the outcome, but the runner only polls and cleans up.  
   Gain 3, Work 2, Harm 3
   Disposition: keep After a person merges a story's last part, `forge next` already prints "Every part ... is merged; record its outcome" (nextstep.py:672), as it does today; the outcome sentence is the coordinator's words and opens a separate fix, so it is outside Done-when 1 to 6 (named in Notes under Not in this story).

10. Blocking: Older pinned repos can build unattended before upgrading.  
    Raise: Not done  
    Case: normal use - a remembered repo uses an older release with `tools = "both"` and has a started fix.  
    The plan scans it like every other remembered repo. [repo.check_pin](/src/forge/repo.py:992) runs its older release, whose [route](/src/forge/repo.py:856) permits a kit without a chat for `tools = "both"`. That contradicts the plan’s stated upgrade limit.  
    Gain 4, Work 2, Harm 2
    Disposition: cut The runner skips a repo whose pin is not this release (`repo._pin(sync.read(...)) != __version__`, the test `doctor.tidy_finished` already makes), so no older release runs without a chat.

11. Blocking: The overlapping-scope test contradicts the existing stacking rule.  
    Raise: Plan gap  
    Case: normal use - stacking is enabled and a reviewed base is still waiting for checks.  
    The plan starts everything returned by `startable` but also says overlapping parts never run together. [task.can_start](/src/forge/task.py:543) permits a stacked child to share its base’s scope before that base merges.  
    Gain 4, Work 2, Harm 3
    Disposition: cut With no stacking by the runner (see finding 5) a part never starts on a base that has not merged, so overlapping scope never runs together; the test now says so, also with `stack` on.

12. Blocking: The detached runner’s Python command does not identify Forge’s environment.  
    Raise: Plan gap  
    Case: normal use - Forge is installed with the documented `uv tool install` command.  
    The plan names `python -c`, while [land._child](/src/forge/land.py:958) uses Forge’s interpreter and package path. In this checkout, `python` is absent and the available `python3` cannot import Forge, so the named command would not start the runner.  
    Gain 5, Work 1, Harm 3
    Disposition: cut The plan now starts the runner with `sys.executable -c` and Forge's own source folder first on the path, as `land._child` does.

13. Blocking: CI tests also wake the machine-wide runner.  
    Raise: Functional  
    Case: normal use - a self-hosted GitHub Actions job shares the developer’s account and remembered repos.  
    The wake rule excludes workers and selected hooks, but not CI. The generated workflow runs `forge test` in each test group ([forge.yml](/.github/workflows/forge.yml:103)); a successful test can therefore start work in remembered repos using the CI job’s environment.  
    Adds work: exclude CI test jobs from waking the runner; F 3 x H 2 = 6; 2 x C = 2  
    Gain 4, Work 1, Harm 3
    Disposition: cut `runner.wake` returns at once when `CI` is set; `tests/conftest.py` already clears `CI`, so the runner tests still wake it.

14. Blocking: P1 Gate: `Design: none` covers a changed owner flow.  
    Raise: Gate  
    Case: normal use - an owner approves work and later responds to a desktop notice.  
    The plan replaces the coordinator’s existing start-and-watch flow with background work and new owner notices ([plan](/plans/FORGE-RUNNER-1.md:7)). Its reason for `Design: none` addresses screens but not that changed flow.  
    Gain 4, Work 2, Harm 2
    Disposition: cut The Design line now states the changed flow in one sentence (approve, Forge builds and merges, a notice only when one item needs you), with no screen added.

15. Blocking: RUNNER and STOPS both own the same production files without a pinned shared seam.  
    Raise: Plan gap  
    Case: normal use - STOPS starts after RUNNER merges.  
    Both tasks claim `runner.py` and the guide files ([task table](/plans/FORGE-RUNNER-1.md:68)). RUNNER does not pin the stop, park and notice interfaces that STOPS needs, while the review contract assigns shared production files to the first task and later tasks to their own files.  
    Gain 4, Work 2, Harm 2
    Disposition: cut The plan pins a seam: RUNNER's first commit adds `stops.py` stubs and all call sites in `runner.py` and `land.py`, plus one crossing test; RUNNER owns every guide file; STOPS edits only `stops.py`, `machine.py` and `brief.md`, and waits through After.

Not checked: runtime tests. `forge next` could not finish because the read-only sandbox blocked its lock.

## Round 2

16. Blocking: An owner’s stop can be cleared or bypassed by other merge commands.  
    Raise: Security  
    Case: normal use - the owner stops one item, then the coordinator runs `forge land --all` for the remaining work.  
    The queue checks the item’s existing state, not the new stop file, and its children lack `FORGE_RUNNER` ([land.py](/src/forge/land.py:516), [land.py](/src/forge/land.py:958)). Under the new rule, a child therefore lifts the stop as if the owner had continued that item. `forge merge` also has no specified stop check.  
    Gain 5, Work 2, Harm 4
   Disposition: cut One check in `task.require_active`, which every path that builds or merges an item already passes (`forge land <item>`, `forge land --all` and its queue children, a train member's merge, `forge merge`), refuses a stopped item; only a person's single-item `forge land <item>` lifts the stop, never a queue child or `--all` (Done-when detail 5).

17. Advisory: A stopped item cannot be continued while its old check wait holds the land lock.  
    Raise: Plan gap  
    Case: normal use - the owner stops an item during a long check wait, then asks to continue it.  
    The plan leaves the old land process alive and holding the lock until checks finish. It also says a second land must refuse without changing anything, although a hand-run land is the way to lift the stop ([plan](/plans/FORGE-RUNNER-1.md:54)). Checks can remain queued indefinitely ([checks.py](/src/forge/checks.py:353)).  
    Gain 3, Work 2, Harm 3
   Disposition: cut `forge stop <item>` now ends the process of the item's live check wait (the land process), which frees the land lock, and a land run between steps exits at its next `task.require_active`; a hand-run `forge land <item>` then continues it (Done-when detail 5, with a test).

18. Advisory: A short GitHub outage bypasses the new retry rule.  
    Raise: Functional  
    Case: normal use - GitHub remains unavailable through its built-in read retries, then recovers.  
    The read becomes a refusal ([github.py](/src/forge/github.py:233)). Land prints `needs you` for that refusal ([land.py](/src/forge/land.py:196)), so the plan parks it immediately instead of applying its promised 10- and 30-second retries.  
    Gain 4, Work 2, Harm 2
   Disposition: cut The runner checks first whether a non-zero exit shows a network problem or the GitHub-read refusal (the test `land._queue` uses), and then retries it twice, 10 s and 30 s later, even though `land` printed "needs you" (Done-when detail 1, with a test).

19. Advisory: Unproven: item 4: a human-merge pull request sends its link in a notice.  
    Raise: Test  
    Case: normal use - the repo uses the default human-merge setting.  
    The human-merge test advances the stubbed merge without checking a notice, while the notifier test checks only a builder question ([plan](/plans/FORGE-RUNNER-1.md:59)). Both can pass if no pull-request notice is sent.  
    Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)

20. Advisory: The machine-wide runner identity has no specified writer.  
    Raise: Plan gap  
    Case: normal use - Forge is used again while a runner is already active.  
    Wake reads a machine-wide `runner.json` to identify that runner, but the plan assigns no task to write its process identity. The only specified record is a different, repo-local file for stops ([plan](/plans/FORGE-RUNNER-1.md:52)). Without the identity, wake cannot signal the active runner.  
    Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)

21. Advisory: A settings fix cannot complete unattended under the stated worker rule.  
    Raise: Functional  
    Case: normal use - a settings fix is started with `forge.toml` in its Done-when and no chat remains open.  
    Naming the file protects the edit, but the worker brief still tells builders never to edit it ([worker.py](/src/forge/worker.py:42)). The planned settings flow still needs the coordinator to make the change, contrary to the unattended fix path.  
    Gain 3, Work 2, Harm 3
   Disposition: cut A fix whose Done-when names `forge.toml` now gives its builder an exception to "Workers never edit `forge.toml`" (`worker.SETTINGS` and `src/forge/templates/brief.md`, both in RUNNER's scope), so it completes with no chat (Done-when detail 1 Settings and 2, with a test).

Not checked: runtime tests. `forge next` could not acquire its lock in the read-only sandbox.
