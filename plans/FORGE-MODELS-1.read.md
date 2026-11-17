---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-17T18:59:40.304843+00:00
seconds: 652.655
read_hash: 54cc2dedbb08e074152799e84b37a5494aa29260
round: 1
passed: no
doc_seen: 54cc2dedbb08e074152799e84b37a5494aa29260
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a1ead7-3a12-77c3-a88d-2804564d95aa
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

1. **Blocking: Not done: Codex builds check a different executable from the one that runs them.**  
   Raise: Not done  
   Case: normal use - A repo uses the installed Codex SDK, while the separate `codex` on PATH is missing or has a different model list. [codex_turn.py](/src/forge/codex_turn.py:144) starts the SDK’s bundled executable, but the plan resolves against the PATH executable. The proposed test replaces the bundled executable with the PATH stub, hiding the difference. [test_codex_worker.py](/tests/test_codex_worker.py:45)  
   Gain 5, Work 3, Harm 3
   Disposition: cut - each round now asks the program that runs it: kit rounds ask the SDK's bundled program (checked: 0.159.2, newest Sol gpt-6.1-sol), reviews and session rounds ask CODEX_BIN or codex (0.169.0, gpt-6.2-sol); What changes says Forge's copy can lag; test_1 gives the two programs different lists through STUB_BUNDLED_CODEX.

2. **Blocking: Not done: Continued native rounds can keep the old model.**  
   Raise: Not done  
   Case: normal use - A newer Sol becomes available between two rounds in the same Codex session. [native.py](/src/forge/native.py:101) continues the existing reader or worker without checking its model; continuing that subagent does not select a new model. The new round can therefore report the newly resolved name while the old subagent still runs.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - native records keep the round's exact model; resumable and offer continue a subagent only when the model is the same (or unrecorded), else start a new one with the reason; test_5 proves it.

3. **Blocking: Not done: A full model name can fall back to another model in review.**  
   Raise: Not done  
   Case: normal use - A repo selects `gpt-6-sol` for review, but the account cannot access it. The pinned Autoreview helper retries with `gpt-6-luna`; Forge recognizes that fallback in [autoreview.py](/src/forge/autoreview.py:76). The plan leaves this path unchanged, although it promises full names stay exact.  
   Gain 4, Work 2, Harm 3
   Disposition: keep - Autoreview's own retry happens only for the full names gpt-6-sol and gpt-5.6-sol on an account without access, and the record already names the model that ran; it is now an accepted limit in Risks and owner question 4.

4. **Blocking: Not done: The model list is cached across multiple rounds.**  
   Raise: Not done  
   Case: normal use - A newer model becomes available while `forge land` is building and reviewing a change. [land.py](/src/forge/land.py:91) runs build, review and a possible fix round in one process, so the planned process-wide cache does not check the list again when each round starts.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - no cache at all: each exact() call with a short name reads the list again, so each round in forge land sees the list as it is when it starts.

5. **Blocking: Functional: Starting an idea hands Codex an unresolved short name.**  
   Raise: Functional  
   Case: normal use - In a new repo, a Codex session runs `forge start` with the planned `sol` explore default. [intake.py](/src/forge/intake.py:42) passes that entry directly to the native offer; none of the planned resolver calls covers it. The generated explorer role also omits the short model, so it cannot supply the configured model itself.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - native.offer resolves its models first, before hold, which covers forge start's idea explorer and session reads; test_5 checks the offer's model.

6. **Blocking: Not done: A missing helper model can be refused after the round takes its place.**  
   Raise: Not done  
   Case: normal use - A Codex design round has an available design model but its configured `luna` helper is unavailable. [worker.py](/src/forge/worker.py:214) selects the design entry first; the planned resolution of the build or lite helper happens later in [codex.py](/src/forge/codex.py:568), after the worker has taken its place and committed its round state. The plan promises the refusal before those actions.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - worker.work resolves the chosen entry and, for a kit round, the kind's entry with its helper pair before holding; test_3's helper case checks a design round with a missing luna helper stops before any slot, commit or thread.

7. **Blocking: Not done: A Claude review’s line and live board still show the short name.**  
   Raise: Not done  
   Case: normal use - A review uses `sonnet`. [autoreview.py](/src/forge/autoreview.py:71) prints and records the name Autoreview reports, while the planned exact name is extracted only after the review in [review.py](/src/forge/review.py:984). The proposed review test checks the final record and arguments, not the line or live board.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - at a Claude review's end Forge prints Claude ran <exact> for <short>, records it as progress and in the run record; the board during the review keeps the short name, named as an accepted limit in Risks; test_2 checks the line.

8. **Blocking: Plan gap: The repeated-work test expects calls and settings that do not occur.**  
   Raise: Plan gap  
   Case: normal use - The planned test runs the same task again with a note. [worker.py](/src/forge/worker.py:204) uses the fix settings for that later round and resumes the conversation. The test configures only the build setting and expects another `thread/start`; the existing boundary test observes `thread/resume` instead. [test_codex_worker.py](/tests/test_codex_worker.py:334)  
   Gain 4, Work 1, Harm 2
   Disposition: cut - test_1's work step sets build and fix to sol and expects the later round's thread/resume config, as test_codex_worker.py:329-337 does.

9. **Blocking: Plan gap: The defaults task leaves an affected test outside its scope.**  
   Raise: Plan gap  
   Case: normal use - A new client starts an idea with Claude. [test_start_sorts_ideas.py](/tests/test_start_sorts_ideas.py:42) expects the current full Haiku name from the new repo, but the planned default makes the offer say `haiku`. That test is absent from the defaults task’s allowed test list.  
   Gain 4, Work 1, Harm 2
   Disposition: cut - the defaults part lists all 24 candidate tests from a search for init plus a default name, test_start_sorts_ideas.py included, and may change only their expected names.

10. **Blocking: Unproven: item 2: Claude cold-read notes can retain the short name.**  
    Raise: Test  
    Case: normal use - Claude reads a plan through its SDK with `sonnet` configured. [story.py](/src/forge/story.py:314) does not pass the SDK run’s recorded model to the note writer, and the proposed Claude test covers a worker and review but no cold read. Those tests could pass while the notes still say `sonnet`.  
    Gain 3, Work 2, Harm 3
    Disposition: cut - _sdk_read returns the run's recorded model and story.read passes it to read_result; test_2 adds a Claude cold read whose notes must name claude (claude-sonnet-5-5).
