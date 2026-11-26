---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-26T12:41:54.377087+00:00
seconds: 575.035
read_hash: 8679d85f39e4348fabc4a180ea340bf8d7c4994f
round: 3
passed: yes
doc_seen: 8679d85f39e4348fabc4a180ea340bf8d7c4994f
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 51fb7480b256b1782b351b8b87998df8aeaf4a7e
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a217c0-ad7c-7862-9823-dc64613a3803
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

1. Blocking: An agent can submit an approval through a helper.
   Raise: Security  
   Case: normal use - A coordinator delegates a task whose message is the approval line. The plan accepts any matching `UserPromptSubmit` payload, but Codex’s [spawn handler](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs) sends that message as user input, and its [hook runtime](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/core/src/hook_runtime.rs) dispatches the prompt hook for it. The planned tool-payload test does not cover this path.  
   Not done: item 2 requires approval to come from the owner’s own message.  
   Gain 5, Work 2, Harm 4
   Disposition: cut the hook now refuses a message that Codex marks as a helper agent's message; the builder reads the real Codex payload for that mark, tests with a captured helper payload, and stops to ask if Codex gives no such mark. The owner text now says a helper's message is ignored.

2. Blocking: Six hexadecimal characters do not securely identify the approved text.
   Raise: Security  
   Case: normal use - An agent that can edit a plan can search for different approval sections with the same 24-bit code, obtain a clean read for the changed plan, and have the owner’s old line approve it. The plan at [line 36](/plans/FORGE-CODEXAPPROVE-1.md:36) replaces the full digest checked by [approval.py](/src/forge/approval.py:247) with its first six characters.  
   Not done: item 2 requires a changed approval text to be refused.  
   Gain 5, Work 3, Harm 4
   Disposition: keep the owner fixed a 6-character code (Decided line added to Notes); grinding plan text for a matching code is deliberate abuse, not normal use, and a changed plan still needs a clean read first.

3. Blocking: The planned replay check uses a prompt event ID that Codex does not send.
   Raise: Plan gap  
   Case: normal use - The owner sends the approval line in a Codex chat. The [Codex hook schema](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/hooks/src/schema.rs) supplies a session ID and active turn ID, but no prompt event ID or `tool_use_id`; the existing check in [approval.py](/src/forge/approval.py:112) requires the latter. A turn ID alone also does not distinguish two messages sent during one active turn.  
   Not done: items 1 and 2 require a real typed approval and replay refusal.  
   Gain 5, Work 2, Harm 3
   Disposition: cut replay marker now uses the payload's session id and turn id (a missing one refuses with no_identity); no prompt event id is expected. Two messages in one turn that both approve record once, and the second says why.

4. Blocking: The new hook is not trusted automatically in the owner’s Codex chat.
   Raise: Functional  
   Case: normal use - After setup or upgrade, the owner types the requested line before reviewing the new hook. [Codex skips new hooks until they are trusted](https://developers.openai.com/codex/hooks), while [Forge’s automatic trust](/src/forge/codex_turn.py:187) applies to threads Forge starts, not the interactive coordinator chat. The planned command test bypasses this host check.  
   Not done: item 1 requires the typed line to record approval.  
   Gain 5, Work 2, Harm 3
   Disposition: cut item 3 and the owner text tell the coordinator to run forge next after the line and, if the story still waits with no reason, have the owner trust the new hook with /hooks in Codex; the What each repo gets bullet says the owner trusts it once.

5. Blocking: A teammate with the previous Forge release silently ignores the new approval line.
   Raise: Functional  
   Case: normal use - A teammate pulls an upgraded repo before updating Forge on their machine. The [hook launcher](/src/forge/sync.py:80) uses the installed `forge`, and [the CLI](/src/forge/cli.py:150) skips the version check for hooks. The earlier [approval handler](/src/forge/approval.py:64) ignores a prompt event, so the line records nothing and gives no reason.  
   Not done: items 1 and 2 cover recording or explaining the refusal.  
   Gain 4, Work 2, Harm 3
   Disposition: cut same forge next check also tells the coordinator to confirm the installed Forge is the release the repo pins; a silent older Forge now shows as a story still waiting with no reason.

6. Blocking: The code does not cover all the text the owner was shown.
   Raise: Not done  
   Case: normal use - After the plan is shown, its Why or Risks text changes and the new read passes. [The section hash](/src/forge/story.py:676) covers only “What changes for you” and “Done when,” so the old code remains valid for the changed text. That contradicts [the plan’s promise](/plans/FORGE-CODEXAPPROVE-1.md:8) to refuse when the shown story changes.  
   Gain 4, Work 2, Harm 3
   Disposition: cut wording fixed above the builders line. The code binds the approved part only (What changes for you and Done when), as Plan mode does, and the owner text now says so instead of promising to catch any change.

7. Blocking: The shipped coordinator instructions still require Plan Mode.
   Raise: Plan gap  
   Case: normal use - A Codex coordinator reads the generated repository instructions before approving a story. [The adapter template](/src/forge/templates/adapters/AGENTS.md:86) says approval is through Plan Mode and there is no other approval step. The task’s [scope](/plans/FORGE-CODEXAPPROVE-1.md:44) omits that template and its generated `AGENTS.md`, leaving them in conflict with the new guide.  
   Not done: item 3 requires usable coordinator guidance.  
   Gain 4, Work 2, Harm 3
   Disposition: cut scope now includes src/forge/templates/adapters/AGENTS.md and the generated AGENTS.md; item 3 updates their Plan Mode sentence (also docs/guide.md and docs/specs/plan-approval.md).

8. Blocking: The existing Plan Mode question loses its instructions and breaks retained tests.
   Raise: Not done  
   Case: normal use - A coordinator already in Plan Mode follows `forge next`. The plan [replaces the question instructions](/plans/FORGE-CODEXAPPROVE-1.md:38), although the question handler still requires the full digest and exact choices in [approval.py](/src/forge/approval.py:237). [The existing approval test](/tests/test_approval.py:11) and [guide test](/tests/test_shortplan_docs.py:71) also depend on that output and are absent from the Tests cell.  
   Gain 4, Work 2, Harm 3
   Disposition: cut item 3 keeps the question text, id and choices unchanged for a Codex chat in Plan mode and adds the typed line first; the question handler is untouched; tests/test_shortplan_docs.py, test_setup.py, test_approval.py and test_contracts.py are now in the Tests cell.

9. Blocking: The tests do not prove the code belongs to the named story.
   Raise: Test  
   Case: normal use - Two stories wait for approval, and the owner enters one story’s key with the other story’s code. The existing [candidate lookup](/src/forge/approval.py:119) matches by digest, not key. A test using a code that matches no story can pass while this line approves the other story.  
   Not done: item 2 requires a code that does not match the named story to record nothing.  
   Gain 3, Work 2, Harm 3
   Disposition: cut the typed path looks up only the named key and compares its code to that story's digest; Done when 2 says so and a test with two waiting stories (A's key with B's code) records neither.

10. Blocking: A mistyped code can be ignored without an explanation.
    Raise: Test  
    Case: normal use - The owner mistypes one of the six characters or omits one. [The plan](/plans/FORGE-CODEXAPPROVE-1.md:36) says other prompts print nothing, and its wrong-code test can use a well-formed six-character code. That test can pass while malformed approval lines are silent.  
    Not done: item 2 requires a wrong code to say why nothing was recorded.  
    Gain 3, Work 2, Harm 3
   Disposition: cut new bad_line refusal for a line that starts like an approval but is malformed; tests for a short and a non-hex code; unrelated prompts stay silent.

11. Blocking: `Design: none` excludes the changed approval flow.
    Raise: Gate  
    Case: normal use - The owner moves from the Plan Mode question to typing an approval line in the chat. [The plan](/plans/FORGE-CODEXAPPROVE-1.md:13) declares no design and marks the task non-user-facing, so [the worker](/src/forge/worker.py:620) also omits the functional check. This read requires a design for a changed flow.  
    Adds work: design the changed chat flow; F 2 x H 2 = 4; 2 x C = 4  
    Gain 4, Work 2, Harm 3
   Disposition: cut the Design line now describes the flow in one sentence; User-facing stays no (no screen exists, so the screen design and rendered checks have nothing to check), with the reason in Notes.

12. Blocking: A stale-code refusal can stop the prompt before the coordinator can show the new story.
    Raise: Plan gap  
    Case: normal use - The owner submits a stale code. The existing [approval handler](/src/forge/approval.py:70) raises the refusal, and the [hook launcher](/src/forge/sync.py:66) turns it into exit code 2. [Codex treats that as a blocked prompt](https://developers.openai.com/codex/hooks), so the coordinator cannot automatically show the new text and code. The planned direct command test does not exercise that host behavior. The host behavior here is based on published source; it was not checked live.  
    Not done: item 2 requires the stale approval to be refused and explained.  
    Gain 3, Work 2, Harm 3
   Disposition: cut a refusal on the typed path is caught, saved with last_refusal, printed as context and exits 0 so the prompt is not blocked; test checks exit 0 and the reason on stdout.

## Round 2

13. Blocking: A Forge question can approve a story without an owner reply.
    Raise: Security  
    Case: normal use - A coordinator runs `forge ask "approve <KEY> <code>"`. [Forge passes the question unchanged](/src/forge/ask.py:27) to a new Codex thread and [trusts its project hooks](/src/forge/codex_turn.py:187). That root thread has no [subagent marker](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/core/src/hook_runtime.rs), so the planned helper check misses it. The real host hook can then record the agent-authored line, despite the question being read-only. This follows the code path; it was not checked live.  
    Not done: item 2 requires a line from anything other than the owner’s message to record nothing.  
    Gain 5, Work 3, Harm 4
   Disposition: cut messages in Codex chats that Forge started (FORGE_WORKER=1, including forge ask) never approve; tested; direct Codex outside Forge is an accepted limit.

14. Advisory: Adding the hook breaks two existing tests omitted from the task.
    Raise: Plan gap  
    The new Codex hook makes doctor probe six distinct event-and-command pairs, while [the Codex setup test](/tests/test_codex_setup.py:126) expects five. It also makes eleven host hooks, while [the launcher tests](/tests/test_fix_hooks_find_forge_in_uv_tool_folder.py:88) expect ten and an exact ten-command log. Neither file is in the task’s Tests cell.  
    Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)

15. Advisory: The malformed-line rule conflicts with its own ordinary-message example.
    Raise: Plan gap  
    [The plan](/plans/FORGE-CODEXAPPROVE-1.md:39) says `approve the plan please` is silent, but it also says to refuse a message starting with `approve` and a word shaped like a story key. [Story keys](/src/forge/story.py:72) can consist only of letters, and the new rule accepts either case, so `the` has that shape.  
    Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)

16. Advisory: An earlier refusal can hide the reason the new hook did not run.
    Raise: Functional  
    Case: normal use - An earlier approval was refused, then the owner tries the new line while its hook is untrusted. [Forge stores one shared last refusal](/src/forge/approval.py:100), and [forge next shows it for a waiting story](/src/forge/nextstep.py:797). The new guidance checks for a wait *without* a reason, so the old reason can prevent it from identifying the skipped hook.  
    Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)

## Round 3

17. Advisory: Not done: item 2 requires a reason for an approval line from a non-owner, but Forge-started chats are silent.
    Raise: Not done  
    Case: normal use - A coordinator sends `forge ask "approve <KEY> <code>"`. [Forge passes the question to Codex](/src/forge/ask.py:27), but [the amended plan](/plans/FORGE-CODEXAPPROVE-1.md:40) requires the hook to print nothing. Its test also requires silence, so it does not prove the explanation promised by item 2.  
    Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)
