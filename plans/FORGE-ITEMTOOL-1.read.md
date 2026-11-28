---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-28T01:33:57.249013+00:00
seconds: 495.537
read_hash: 68c0449c94215f2c60baa940018e819379ed95ed
round: 1
passed: no
doc_seen: 68c0449c94215f2c60baa940018e819379ed95ed
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21fc2-1aee-7260-9b38-3dc722fffc9e
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

1. **Blocking: The planned option declaration breaks command parsing.**  
   Raise: Plan gap - The plan adds `("--tool", {...})` to the command arguments. [cli.py](/src/forge/cli.py:79) expands the first value as argument names, so the string is expanded character by character and raises `ValueError`. The existing declarations use `("--tool",)` as a tuple.  
   Case: normal use - Running `forge work` after adding the option.  
   Gain 5, Work 1, Harm 3
   Disposition: cut - the option is declared as a tuple of names, `(('--tool',), {...})`, as the existing commands do (Done-when details 1 and 2).

2. **Blocking: Not done: item 1: a plain round erases the saved choice.**  
   Raise: Not done - The plan says to assign `state["tool"] = args.tool` on every round. The runner calls plain `forge land` with no tool option ([runner.py](/src/forge/runner.py:251)), so its first round uses the saved builder and then writes `None` over it. A repair can then use the repo default.  
   Case: normal use - A fix starts with a chosen builder and needs a repair round.  
   Gain 5, Work 1, Harm 3
   Disposition: cut - a round saves `state["tool"]` only when `--tool` is given, so a plain round or the runner never clears it (details 1).

3. **Blocking: Starting a fix through Forge's normal intake will crash.**  
   Raise: Functional - The planned `args.tool` access in `fix_start` is unconditional, but [intake.py](/src/forge/intake.py:190) calls it with no `tool` attribute. The same is true for a split follow-up in [close.py](/src/forge/close.py:555). Both paths would raise `AttributeError`.  
   Case: normal use - `forge start` chooses the fix lane.  
   Gain 4, Work 1, Harm 3
   Disposition: cut - `fix_start` and `start` read the option with `getattr(args, "tool", None)`, so the `forge start` and follow-up callers work, and a test covers `forge start` (details 2).

4. **Blocking: Not done: item 1: Antigravity repairs do not use the promised fix model.**  
   Raise: Not done - For a non-design task, [worker.py](/src/forge/worker.py:213) selects `Build` for every Antigravity round, including repairs. The plan expects `[models.fix.antigravity]` without changing that selection; the existing repair test instead expects the build model ([test_antigravity_build.py](/tests/test_antigravity_build.py:140)).  
   Case: normal use - A task built on Antigravity needs a repair.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - the plan no longer promises `[models.fix.antigravity]`; it names the entry each builder reads (build, lite or design on Antigravity, fix only on Codex repairs) and the test expects the build entry (details 1).

5. **Blocking: Not done: item 3: start and switch do not check whether Claude or Codex is installed.**  
   Raise: Not done - The shared check in the plan checks installation only for Antigravity. The Claude and Codex checks remain in [worker.ready](/src/forge/worker.py:477), which the start and switch paths do not call. They can save a choice for a missing SDK and fail only when work begins.  
   Case: normal use - Start a fix or switch a stuck item to a builder whose SDK is missing.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `check_tool` checks Claude, Codex and Antigravity installs and is called by work, land, both start commands and the switch (details 3).

6. **Blocking: Not done: item 3: work can merge changes before refusing a builder.**  
   Raise: Not done - [repo.check_pin](/src/forge/repo.py:953) calls `worker.prepare` before the work handler. [prepare](/src/forge/worker.py:149) merges the default branch before the planned tool check or existing readiness check runs. The plan also excludes the file containing that earlier call from Scope.  
   Case: normal use - The default branch has advanced when a user chooses a missing or disallowed builder.  
   Gain 4, Work 3, Harm 3
   Disposition: cut - `check_pin` passes the option to `prepare`, which runs `check_tool` before the default branch is merged; `cli.py` and `repo.py` (`check_pin` only) join SAVE's Scope, and a test proves nothing is merged on refusal (details 1 and 3).

7. **Blocking: Not done: items 1 and 3: land can skip both saving and checking the choice.**  
   Raise: Not done - The plan passes the option only to `worker.work`. For an already-built item, [land.py](/src/forge/land.py:125) can go straight to close without calling the worker. It can therefore ignore a valid choice, or close the item without refusing a missing or disallowed builder. The planned land test starts with an unbuilt item and does not cover this path.  
   Case: normal use - Resume closing an item that already has a build.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `forge land` itself checks and saves the choice before close, so an already built item is covered; a test covers it (details 1).

8. **Blocking: Not done: item 4: the shared check changes the existing switch without an option.**  
   Raise: Not done - The plan calls the tool check for every switch and rejects a family excluded by `tools`. Today [close.py](/src/forge/close.py:130) saves the other family, and [repo.worker](/src/forge/repo.py:804) honours that saved choice. With `tools = "claude"`, an unqualified switch from Claude to Codex would now be refused, contrary to the promised unchanged mapping.  
   Case: normal use - A single-tool repo switches a stuck worker.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - the switch checks only when `--tool` is given; a switch with no option keeps today's mapping with no check, and a test covers `tools = "claude"` (details 4).

9. **Blocking: SAVE ships new coordinator options without the required guide update.**  
   Raise: Gate - SAVE adds four options, but the plan assigns the template guide update to the later SWITCH task. The repo's [review rule](/AGENTS.md:139) requires that guide or worker-brief update in the same change and calls its absence P1.  
   Case: normal use - SAVE is reviewed and merged before SWITCH.  
   Gain 4, Work 1, Harm 1
   Disposition: cut - SAVE's Scope now includes `skill.md` and writes the guide for its four commands; SWITCH adds the switch paragraph (details 5).

10. **Advisory: The chosen builder disappears from `forge next` after a build.**  
    Raise: Functional - [nextstep.py](/src/forge/nextstep.py:1149) shows the builder only beside a `forge work` next step. After a completed round, the normal next step is `forge close`, so the item is shown without the choice even though the plan says `forge next` shows it.  
    Gain 3, Work 2, Harm 2
   Disposition: cut - the claim is narrowed: `forge next` names the builder beside a `forge work` step, as it does today; `nextstep.py` is at the size ceiling and is not extended.

11. **Advisory: A refused start gives a next command for an item that was never created.**  
    Raise: Functional - The planned `tool_off` refusal always suggests `forge work {item} --tool {tools}`, including for `fix start` and `task start`. Those commands have not created the item when the check refuses, so the suggested work command cannot proceed. [task.py](/src/forge/task.py:274) creates the checkout only after the start checks.  
    Gain 3, Work 1, Harm 2
   Disposition: cut - `tool_off` now gives a next step that does not name a work command for an item that does not exist yet (details 3).

12. **Advisory: The planned `forge next <item>` test cannot run.**  
    Raise: Plan gap - The plan asks the test to run `forge next BOARD/HELP`, but [nextstep.py](/src/forge/nextstep.py:27) declares no arguments for `next`; [cli.py](/src/forge/cli.py:134) refuses the extra item.  
    Gain 2, Work 1, Harm 1
   Disposition: cut - the test runs `forge next` with no argument in the item's folder (details 1).

Skipped `forge next`: it can change repository files.
