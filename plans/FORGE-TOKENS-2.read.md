---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-26T12:40:09.455064+00:00
seconds: 677.803
read_hash: 58d90cf9b159d4f3221bc347fbc85e4e9870e71e
round: 1
passed: no
doc_seen: 58d90cf9b159d4f3221bc347fbc85e4e9870e71e
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a217d4-87d7-74f0-b969-c62a1425eb07
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

1. Blocking: Not done: item 3: the default Codex provider ignores the keep-instruction.
   
   Raise: Not done  
   Case: normal use - a builder using OpenAI reaches the shortening limit.  
   [Forge pins Codex 0.171.0](/src/forge/codex.py:34). Its [provider code](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/model-provider/src/capabilities.rs#L29-L39) selects remote compaction, whose [request path](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/core/src/compact_remote_v2_attempt.rs) does not use `compact_prompt`. The stand-in test would pass even though the instruction to keep findings, failed tests and tried fixes has no effect.  
   Gain 5, Work 3, Harm 3
   Disposition: cut Checked in Codex 0.171.0: OpenAI providers use remote compaction, which ignores compact_prompt. The plan drops compact_prompt, says Forge cannot make Codex keep a detail, and Done-when 3 now promises only that the next repair brief lists the open findings and failing tests (tested).

2. Blocking: Not done: items 1–3: native Codex builders bypass both planned changes.
   
   Raise: Not done  
   Case: normal use - a Codex coordinator runs a Codex builder with `codex_fast` set to `needed` or `always`.  
   [worker.py](/src/forge/worker.py:199) routes those builders to [native.hand_out](/src/forge/worker.py:335), without calling the planned driver. They receive neither the new shortening limit nor the turn-level effort change, and their [run-end record](/src/forge/native.py:503) has no token counts for the report.  
   Gain 4, Work 4, Harm 3
   Disposition: cut The plan now lists native Codex builders (codex_fast needed or always) as an accepted limit, unchanged and left out of the measure; routing them through the driver is a follow-up.

3. Blocking: Unproven: item 3: the threshold can count only part of the current context.
   
   Raise: Test  
   Case: normal use - a Codex user has selected `body_after_prefix` as the shortening-limit scope.  
   [Forge inherits other Codex settings](/src/forge/codex.py:182), while the plan specifies no scope override or test. With that setting, [Codex counts growth after the retained prefix](https://github.com/openai/codex/blob/rust-v0.171.0/codex-rs/core/src/session/context_window.rs#L53-L73), so current context can exceed 120K well before the configured limit triggers. The proposed config test would still pass.  
   Gain 3, Work 2, Harm 3
   Disposition: cut Item 3 now also sets model_auto_compact_token_limit_scope = "total" and tests it, so a user's body_after_prefix setting cannot change the count.

4. Blocking: Gate: both tasks omit existing tests that their changes make fail.
   
   Raise: Gate  
   Case: normal use - a repair changes effort or a builder starts a new conversation.  
   [test_effort_ladder.py](/tests/test_effort_ladder.py:203) requires effort in the resume config, and [test_models_per_family.py](/tests/test_models_per_family.py:54) compares the entire start config without the new shortening keys. Neither file is named in the [tasks’ Tests cells](/plans/FORGE-TOKENS-2.md:50).  
   Gain 4, Work 2, Harm 2
   Disposition: cut Both tasks now name the existing tests that break: test_effort_ladder, test_worker_and_reader_chats_survive_rounds, test_fix_settings_from_main (EFFORT); test_models_per_family, test_design_route, test_which_worker_builds (COMPACT).

5. Blocking: Unproven: item 2: a replacement conversation can lose the chosen effort.
   
   Raise: Test  
   Case: normal use - Codex reports that an earlier conversation is unavailable, so Forge starts a replacement.  
   [codex_turn.py](/src/forge/codex_turn.py:257) reuses the same settings for resume and fallback. The [existing replacement test](/tests/test_fix_every_fix_round_resends_the_whole_worker.py:75) does not check effort, and the planned tests cover only a first start and a successful resume. They would pass if removing effort for resume also removed it from the replacement start.  
   Gain 3, Work 2, Harm 3
   Disposition: cut Item 2 now keeps the effort in the replacement conversation's start config and on its turn, with a test that deletes the stored conversation.

6. Blocking: Not done: item 3: the promised shortening count is not in Forge’s turn log.
   
   Raise: Not done  
   Case: normal use - a long builder conversation is shortened and the coordinator prepares the after-release report.  
   [codex.py](/src/forge/codex.py:707) writes turn starts and ends to that log, but sends `contextCompaction` only as progress. [Progress records](/src/forge/event_log.py:78) coalesce updates, so they cannot provide the promised count either. The planned after-release proof cannot be produced from the named log.  
   Gain 4, Work 2, Harm 2
   Disposition: cut Checked: the turn log has only turn start and end lines. The contextCompaction count is removed from item 3 and listed as an accepted limit; nothing else needs it.

7. Blocking: Not done: item 1: the measurement recipe does not produce the promised comparison.
   
   Raise: Not done  
   Case: normal use - the measured weeks contain both story tasks and standalone fixes.  
   [The plan](/plans/FORGE-TOKENS-2.md:42) lists four fields, then defines uncached input as the second minus the third: effort minus input tokens. It also groups by effort change and family, but not item kind; [Forge uses different work kinds](/src/forge/worker.py:210) for tasks and fixes. A change in their mix can therefore appear as a change caused by the release.  
   Gain 4, Work 1, Harm 2
   Disposition: cut Item 1 now says uncached input is input_tokens minus cached_input_tokens, groups by item kind (task or fix) as well as family, and leaves out native rounds that have no token counts.
