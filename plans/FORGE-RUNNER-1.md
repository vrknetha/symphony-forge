# Approved work keeps moving to merge without reminders

2 parts · Risks: none one-way; five accepted limits · New moving parts: one background runner process per computer

## What changes for you

- After you approve a plan, Forge starts every part that nothing blocks, builds it, checks it and merges it. You send no more messages. A part that waits for another part starts as soon as that part has merged. A fix that you start with Forge goes the same way, from its start to its merge. (Source: the owner's choice, 26 Nov 2026)
- One helper, the runner, does this in the background. Forge starts it by itself when you use Forge, approve a plan or open a chat in a Forge repo. It ends when there is nothing left to do. It is not a system service. After a restart of the computer, it comes back the first time you use Forge. (Source: the owner's choice, 26 Nov 2026)
- When one item needs you, only that item stops, and the other ready work goes on. An item needs you when a builder asks a question, a review loop reaches its round limit, a run is stuck, a fix needs a size decision, a tool needs setup, or a pull request (the request to merge the change into the main code) must be merged by a person. You get one desktop notice with the question or the pull request link. When all the work is done, you get one summary notice. (Source: the owner's choice, 26 Nov 2026)
- A stop that you set stays after a restart. Forge builds that item again only when you tell your agent to continue it.
- Status stays on the board and in the next-step report. There is no new screen, no new command and no new setting.
- Your coordinator agent no longer starts each approved part, starts each fix build, watches the background runs, checks the next step after every merge, or copies the queue into the handoff note. It answers the notices and the builders' questions.
- What each repo gets: a new repo and an existing repo both get all of this on upgrade to the release that has this story, and `forge sync` refreshes the guide text. Nothing converts, and no setting changes.

Design: none (no screen changes; the notices are system pop-ups with one or two lines of text)

## Why

Coordinators stop after a plan is approved, so the owner must keep saying "keep going" and asking for status. Each approved part and each new fix then waits until an agent starts it by hand. The owner may ask for ten things at once, and every one of them must keep moving until its pull request has merged and its folder is gone. Forge already knows the whole queue (git, the `.factory` records and GitHub), and `forge land` already builds, checks and merges one item. Nothing runs it without a chat.

## Done when

1. **After one approval, every part of the story that nothing blocks starts, builds and merges (or becomes ready for a person to merge) with no further message from the owner, and a part that waits for another part starts when that part has merged.**
2. **A fix started with Forge is built, checked and merged the same way, and the folder of every merged item is removed.**
3. **An item that needs the owner stops alone, and the other ready work keeps going.**
4. **The owner gets one desktop notice when an item first needs them, with its question or pull request link, and one summary notice when the work is done.**
5. **A restart repeats no finished build and undoes no stop that the owner set, and the runner comes back the first time Forge is used.**
6. **When the work is done, the runner ends and makes no recurring GitHub calls.**

## Risks

Risks: none one-way. Each part reverts with its pull request.

Accepted limits:
- A repo that uses one tool (`tools` set to `claude` or `codex`) now builds with no chat open. If that tool's kit is not installed, Forge stops that item once, sends a notice that names the setup step, and does not switch to the other tool.
- A pull request that a person must merge is checked on GitHub once for each such pull request: every minute at first, then at growing delays up to 30 minutes, for at most 24 hours. After that the runner ends, and the next use of Forge starts it again. A repo with nothing to do makes no GitHub call.
- On Windows there is no pop-up. The same lines show in the next-step report.
- A repo that pins an older Forge release is started and landed through its own release. It builds with no chat only after it upgrades.
- Forge does not form a combined test run for several ready changes from the runner. `forge land --all` still does that when someone runs it.

## For the builders

### Done-when details

1. New module `src/forge/runner.py`. `nextstep.py`, `story.py` and `codex.py` are at 1,200 lines, so none of them changes; `repo.py` gets 3 lines at most.
   - **Wake.** In `cli._run`, after a command returns 0, call `runner.wake(Path.cwd())` (a lazy import). It returns at once when `FORGE_NO_RUNNER`, `FORGE_WORKER` or `FORGE_RUNNER` is set, when the folder is not in a Forge repo, or for a `hook` command other than `hook approval` and `hook context` (the approval and the chat start). Otherwise it calls `machine.remember(top)` and reads `runner.json` in the folder of `machine._repos_file()`. If its `pid` is alive (`codex._alive`, which also checks the start time), it touches `runner.wake`. If not, it starts `python -c "from forge.runner import main; main()"` detached (a new session on Linux and macOS, `DETACHED_PROCESS` on Windows), the way `land._child` starts its child, with `CLAUDECODE` and `CODEX_THREAD_ID` removed from its environment so no round is handed to a chat. The runner first takes `runner.lock` with `codex._try_lock` and exits at once if another runner holds it, so a second start does no harm. Test-only variables, like `FORGE_CHECKS_POLL`: `FORGE_NO_RUNNER=1` (set for every test in `tests/conftest.py`'s `isolated_environment`, after the variables it clears) and `FORGE_RUNNER_TICK`, the seconds between checks (2 by default).
   - **A pass.** The runner works on each `machine.remembered()` repo in turn. It reads local files first: `story.worktrees(top)` with `task.branch_item` for started items, and the story records for approved stories. When it finds no started item and no approved story with an unstarted part, it makes no network call. Otherwise it runs `git fetch -q origin`, then `doctor.tidy_finished(top)`, then starts each part in `nextstep.startable(top)` with the subprocess `forge task start <KEY>/<TASK>`, one at a time. `startable` is the list `forge next` shows, so After links, overlapping scope, stacking limits and the developer assignment already apply, and `task start` checks them again. A refusal such as "already started" (a coordinator was faster) is not a stop. Then, for every started item that is not merged or dropped, with no live run (the checks `land._queue` makes: `machine.entries()` and `board.active_runs`), no round out with a chat (`land._pending`) and not parked, it starts the subprocess `forge land <item>` with `FORGE_RUNNER=1`, up to `machine.half_cores()` at a time. A fix that `forge start` made is such an item. Output goes to `.git/forge/runner.log`. The runner takes no agent place; the build inside `land` waits for its place as it does today.
   - **When a land run ends.** Exit 0 and `land._merged(top, branch)`: merged; another pass starts at once. Exit 0 with the line "is ready; a human merges": the item waits for a person's merge (see Polling). Any other exit 0 (a chat owes a handback, a stacked part waits for its base): the item is quiet and is tried again only after another item merges or `runner.wake` is touched. A non-zero exit: this part keeps the item out of the rest of the runner's life; STOPS makes that lasting and sends the notice.
   - **Polling.** One `land._merged` call per waiting pull request, 60 s after the item was ready, doubling to 30 minutes, for 24 hours at most. A merge starts another pass, whose first step removes the folder.
   - **One-tool repos.** `repo.route` returns "kit" when `FORGE_RUNNER=1`, and does not refuse for a missing session. `worker.ready` then stops with its own words when the SDK or the CLI is missing. STOPS turns that text into the setup notice.
   - Tests (new, run the forge command, reuse the `land` fixture, the gh stub and the agent stub of `tests/test_land.py`): a two-part story whose second part has After on the first, with `merge = "agent"`: after `forge hook approval`, nothing else is run, and both parts merge in order and both folders are gone. With `merge = "human"`: the first part becomes ready, the stub gh reports its merge later, and the second part then starts and finishes. Two parts with overlapping scope never run together. A repo with `tools = "claude"` and no session builds and merges a fix. A coordinator's own `forge task start` for the same part causes no stop.
2. A fix started with `forge fix start` (the step `forge start` ends in) is a started item, and the wake after that command is enough. The runner calls `doctor.tidy_finished` with a `report`, so STOPS can name a folder that local changes keep in place. Test: a fix reaches merge with no other command, and its folder is removed, also when it merges while the runner polls.
3. STOPS. Test: two fixes, and one builder asks a question (a `Question:` paragraph in its handback). The other merges, and the first stays stopped and builds nothing more. A fix that needs a size decision stops the same way.
4. STOPS. A notice is one call to `osascript` (macOS, the text passed as arguments) or `notify-send` (Linux, when installed). A missing notifier is not an error. The title names the repo and the item; the body is the question, the first line of the refusal with its next step, or the pull request link. The summary names the number merged and each item that still waits for the owner. Tests put stub notifiers on `PATH`: exactly one call for the item with the question, none more after repeated wakes or a restart, one summary call at the end, none when a runner started and found nothing to do.
5. STOPS. One small file, `.git/forge/runner.json` (`repo.forge_dir(top)`, written with a temporary file and `os.replace`, as `handoff_hook` does). It holds `{"stopped": [item, ...], "told": {item: {"reason": line, "sig": hash}}}` and is the only new record. `machine.stop` adds the item to `stopped` before it ends the runs (for each run that has an item, and for the named item when nothing runs). `forge land <item>` run by hand (without `FORGE_RUNNER`) removes the item from both. The runner never starts a stopped item. A parked (`told`) item is tried again only when its `sig` changes (the branch head, the state file text and the open question in `codex.record(top, item)`), when its pull request has merged, or when a person runs `forge land` on it. Tests: `forge stop <item>` during a slow stub build, with the runner killed and revived by the next command: the item is not built again, and a hand-run `forge land <item>` lifts the stop. The runner killed with SIGKILL after a finished build and before the close, and again after the merge and before the cleanup: one agent run in the stub's log, one `pr merge` call, the folder gone, and the item merged once. A killed runner's land runs finish by themselves, and the next runner leaves alone any item they still work on.
6. RUNNER. Test: after the last item merges, the runner process is gone within a few ticks, and the stub gh call log does not grow over the next ticks. Also, `forge lanes` in a repo with nothing to do starts a runner that ends with no gh call.

Each new test names its story slug and number as existing tests do, so the rule checks pass.

### Guide text

RUNNER removes from `src/forge/templates/skill.md` the coordinator steps that the runner replaces: starting a part after approval, "run `forge land <item>` for each in the background", the run-and-watch advice for queued work, and "run `forge next` after each merge to start what was unblocked". The "Start this task" and "Land it" rows stay as the way to act by hand. It adds how to see that the runner works (the board and `forge next` show the items) and says to start and land by hand only when a notice says the runner cannot. The flow's step 3 in `src/forge/templates/adapters/AGENTS.md` changes the same way. STOPS adds how to read a notice and how to continue a stopped item (`forge land <item>`). In `src/forge/templates/brief.md`, next to the `Question:` rule, it says that a builder's question stops only its own item and reaches the owner as it is written, so it must make sense alone. Run `forge sync` for `AGENTS.md` and the two generated skill copies.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| RUNNER | A background runner moves approved work to merge | Wake and start of the runner, automatic part and fix starts, builds through `forge land` with no chat, polling of human merges, cleanup, the end of the runner | 1, 2, 6 | `src/forge/runner.py`, `src/forge/cli.py`, `src/forge/repo.py`, `src/forge/templates/skill.md`, `src/forge/templates/adapters/AGENTS.md`, `AGENTS.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_runner_moves_approved_work_to_merge.py` (new), `tests/test_runner_builds_a_started_fix.py` (new), `tests/test_runner_ends_when_idle.py` (new); changed: `tests/conftest.py` | | no | |
| STOPS | Only the item that needs the owner stops, with a notice | Lasting stops and parked items, desktop notices and the summary, the owner's stop that survives a restart | 3, 4, 5 | `src/forge/runner.py`, `src/forge/machine.py`, `src/forge/land.py`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_runner_stops_one_item_and_tells_the_owner.py` (new), `tests/test_runner_restart_repeats_nothing.py` (new) | RUNNER | no | |

New moving parts: one background runner process per computer, started by Forge and ended when its work is done (Done-when 1, 2, 5 and 6); one small file, `.git/forge/runner.json`, for the owner's stops and the items already told to the owner (Done-when 3 and 5)

## Notes

- Source: Astra's design of 26 Nov 2026 (`~/Workdir/forge-handoff-files/astra-queue.log`). The plan keeps its shared eligibility (`nextstep.startable`), its `forge land` reuse, its "park only the affected item" rule and its restart and idle-polling tests. It drops what the owner's fixed choices of 26 Nov 2026 cut: registration with the operating system at login (Forge starts the runner instead), a new board state "Merged · cleanup needs you" (status stays on the board and in the next-step report), and runner-owned settings.
- No new top-level command: Forge is at its limit of 26. The runner starts as a hidden module entry, and tests drive it through the commands that wake it.
- Size estimate, as Astra's: about 250 production lines in RUNNER and about 150 in STOPS, plus 150 to 250 lines of tests.
- Not in this story: merge trains formed by the runner, a Windows pop-up, a setting to turn the runner off, and any change to approvals, exceptions, merge settings, deferred ideas or deployment.
