---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-27T12:44:35.154856+00:00
seconds: 551.614
read_hash: a1696687aa138a45b790c15cd373399224fe7c39
round: 1
passed: no
doc_seen: a1696687aa138a45b790c15cd373399224fe7c39
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21d00-deff-71d2-a1bd-cf2ae06fa405
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

1. Blocking: Not done: item 4: the retry command can execute text from the question.
   Raise: Security — [the plan](/plans/FORGE-ASKFAMILY-1.md:37) uses `json.dumps` to quote the question, as [the current command](/src/forge/ask.py:32) does. JSON double quotes do not prevent shell command substitution.
   Case: normal use - Someone asks about a backtick-quoted shell command, then pastes the suggested retry after a failure. The shell executes that command before starting Forge.
   Gain 5, Work 2, Harm 4
   Disposition: cut the Next line no longer repeats the question: it says `run forge ask again with the same question`, so nothing from the question reaches a shell; the test asks a question with a backtick and `$(...)` and checks it is not in the output (builders item 4).

2. Blocking: Not done: item 4: the proposed test can miss lost edits.
   Raise: Test — [the plan](/plans/FORGE-ASKFAMILY-1.md:40) compares `git status --porcelain`, which does not show the contents of modified files and normally omits ignored files. The [Claude stub](/tests/stubs/claude_agent_sdk.py:103) can change a named file during a read.
   Case: normal use - A developer already has an edited file; a broken read overwrites it, but its status remains modified and the proposed comparison passes.
   Gain 3, Work 2, Harm 4
   Disposition: cut the read-only test now keeps an edited tracked file and an untracked file, lets the stub write to the edited file, and compares file bytes as well as `git status --porcelain` for each family (builders item 4).

3. Blocking: Not done: item 1: Gemini’s answer is not recorded by the proposed turn.
   Raise: Not done — [the plan](/plans/FORGE-ASKFAMILY-1.md:37) reuses `antigravity.read`, but [that turn](/src/forge/antigravity.py:423) collects answer text in memory and returns it; its log receives stderr. [Run records](/src/forge/repo.py:549) retain run details, not the answer.
   Case: normal use - A user needs the Gemini answer after its terminal output is gone.
   Gain 4, Work 2, Harm 3
   Disposition: cut after a Claude or Gemini turn `ask` appends the answer to the item's work log, the file Codex's ask logs to, and a test reads it; Claude's stream already reached its own log (builders item 1).

4. Blocking: Not done: item 3: the proposed reader choice can select the session’s own family.
   Raise: Not done — [the plan](/plans/FORGE-ASKFAMILY-1.md:39) uses `roles.read_family`, which [honors `reviews` and falls back to the current family](/src/forge/roles.py:101) when the other SDK is missing.
   Case: normal use - With both tools enabled, a Codex session and `reviews = "codex"` asks Codex; a missing Claude SDK also selects Codex instead of refusing or installing Claude.
   Gain 4, Work 2, Harm 3
   Disposition: cut the default family is now a plain rule in `ask.py`, `claude` if the session is Codex else `codex`, and ignores `tools` and `reviews`; `roles.read_family` is not used; the Claude and Codex kits install themselves, so a missing SDK is installed and not skipped. Above the line, bullet 3 of What changes and the Accepted limits changed to match (builders item 3).

5. Blocking: Not done: item 4: retrying an explicit model can ask a different family.
   Raise: Not done — [the proposed retry](/plans/FORGE-ASKFAMILY-1.md:40) omits `--model`, although [family selection](/plans/FORGE-ASKFAMILY-1.md:38) depends on it.
   Case: normal use - A Gemini turn fails, and the suggested retry selects Claude or Codex from the session or settings instead.
   Gain 4, Work 1, Harm 3
   Disposition: cut the Next line adds ` and --model <model>` (quoted by `repo.quote`) when `--model` was given, so a retry keeps the family; without `--model` the same settings give the same family (builders item 4).

6. Blocking: Plan gap: the suggested Claude output handling can omit the answer.
   Raise: Plan gap — [the plan](/plans/FORGE-ASKFAMILY-1.md:37) suggests suppressing the final print whenever Claude streamed text. [`_sdk_read`](/src/forge/story.py:1014) streams assistant messages but returns the separate result; [the supplied stub](/tests/stubs/claude_agent_sdk.py:128) gives those different text.
   Case: normal use - Claude streams an intermediate message before its final result, so the suggested handling prints the intermediate message and loses the answer.
   Gain 3, Work 2, Harm 3
   Disposition: cut the Claude turn runs inside `contextlib.redirect_stdout(io.StringIO())` and `ask` prints the final result text once; the test checks the final text prints once and the streamed line does not (builders item 1).

7. Blocking: Unproven: item 1: Gemini cannot inspect the Git changes behind a question.
   Raise: Functional — [the proposed Gemini turn](/plans/FORGE-ASKFAMILY-1.md:37) uses a copy that [excludes `.git`](/src/forge/antigravity.py:170), while its [read profile denies commands](/src/forge/antigravity.py:91). The existing ask test itself uses the question [“What changed?”](/tests/test_ask_command.py:87).
   Case: normal use - A user asks Gemini for a second opinion on uncommitted or branch changes; it has the current files but no baseline or diff to inspect.
   Adds work: provide Git change context to Gemini; F 3 x H 2 = 6; 2 x C = 4
   Gain 3, Work 2, Harm 3
   Disposition: keep Gemini's scratch copy has the current files, uncommitted edits included, but no `.git` and no commands; the owner (27 Nov 2026) wants this stated as an accepted limit and not new code, and it is now written in the plan's Accepted limits.

8. Blocking: Unproven: item 2: an older worktree can select a stale family setting.
   Raise: Test — [the current ask command](/src/forge/ask.py:18) reads the checkout’s configuration directly, while [routing](/src/forge/routing.py:52) takes unchanged model settings from the default branch. The proposed tests use one new checkout and would pass if family selection kept using the stale configuration.
   Case: normal use - The default branch changes `models.ask` from Codex to Claude while a task worktree remains open; an ask there can still select Codex.
   Gain 3, Work 2, Harm 3
   Disposition: cut `ask` reads its config through `routing.routed(top, repo.config(top))` as `codex.run` does, and a test follows `tests/test_fix_settings_from_main.py` test 2 with a task worktree that keeps an old `forge.toml` (builders item 2).

9. Blocking: Plan gap: the planned help change breaks an existing command test.
   Raise: Gate — [the plan](/plans/FORGE-ASKFAMILY-1.md:54) changes the ask help text, but [the shared expected help](/tests/test_split_commands.py:55) still requires the exact Codex-only wording and is [checked through the command](/tests/test_split_commands_rest.py:49). That test file is absent from the task’s Tests cell.
   Case: normal use - The required command help is updated and the existing test fails.
   Gain 4, Work 1, Harm 3
   Disposition: cut `tests/test_split_commands.py` (the expected help line, checked through `tests/test_split_commands_rest.py`) is now in the task's Tests cell and in the Notes (builders table and Notes).

10. Advisory: Plan gap: the prescribed Claude test names the wrong call log.
    Raise: Plan gap — [the plan](/plans/FORGE-ASKFAMILY-1.md:37) names `claude-sdk-calls.jsonl`, but [the stub](/tests/stubs/claude_agent_sdk.py:79) writes plan-mode calls to `claude-calls.jsonl`.
    Gain 2, Work 1, Harm 1
   Disposition: keep - below the bar (live with)

11. Advisory: Split: FAMILY → model and family selection; read-only execution and failure handling.
    Raise: Plan gap — [the task](/plans/FORGE-ASKFAMILY-1.md:47) covers all four Done-when items. A split would need an owner and order for the shared `ask.py` file.
    Adds work: separate a second part; F 1 x H 1 = 1; 2 x C = 4
    Gain 2, Work 2, Harm 1

Not checked: `forge next` could not finish because the read-only environment denied its lock.
   Disposition: keep - below the bar (live with)
