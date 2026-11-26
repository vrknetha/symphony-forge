# Fewer costly rounds: keep the saved prompt and shorten long builder chats

2 parts · Risks: none one-way; three accepted limits · New moving parts: none

## What changes for you

- A repair round that raises the builder's effort (low in round 1, high later) continues the same Codex conversation and changes the effort inside it. The saved prompt is reused instead of paid for again in full. (Source: the owner's choice, 25 Nov 2026)
- A Codex builder conversation that passes about 120K tokens of current context is shortened by Codex's own shortening step. The shortened version keeps the review findings, the failing tests and what was already tried. Forge adds no summary tool of its own. (Source: the number 120K is the owner's choice, 25 Nov 2026)
- After the release, the coordinator compares the uncached input of repair rounds with the week before and tells you the measured change. It reads Forge's existing run records. No dashboard is added.
- Claude and Antigravity builders do not change. Antigravity already changes effort inside its resumed chat. Claude already resumes the same session with the new effort, and Forge cannot control how Claude's service saves the prompt. Claude shortens long chats by its own rules. (Accepted limit)
- What each repo gets: a new repo and an existing repo get all of this on upgrade to the release that has this story. An open builder conversation gets the shorter limit the next time it continues. No setting changes and no command is added.

Design: none (no screen changes)

## Why

A Codex repair round that goes from low to high effort loses the saved prompt: a median of 178K uncached input tokens, against 74K when effort stays the same (items that finished 18 to 25 Nov 2026). Antigravity's Neon kept about 90% cached across the same change. Long builder conversations also reread their whole history on every model call.

Today Forge sends the new effort when it resumes a Codex conversation, as a config setting. Codex does not say that this setting is meant for a resumed conversation. Codex's turn request does take an effort "for this turn and subsequent turns". This story sends the effort there. The story is the first step to find out whether that is the cause of the lost prompt, and the measurement says so.

This is the second story of the split of 25 Nov 2026. The first, FORGE-TOKENS-1, made builder briefs smaller. The owner chose this scope, "reuse, cache-safe, compact", on 25 Nov 2026. Builder self-check, one rerun of a flaky CI failure, a stop after two cold reads, a trial of lower review effort and a token budget per item stay outside this story.

## Done when

1. **Uncached input per repair round is measured before and after the change on the same kind of item, and the change is reported with those numbers.**
2. **A repair round that changes effort keeps most of its cached input in the same conversation.**
3. **A builder conversation over about 120K tokens is shortened, and its findings, failing tests and tried fixes are still there afterwards.**

## Risks

Risks: none one-way. Each part reverts with its pull request.

Accepted limits:
- Forge's tests use a stand-in Codex server, so they prove what Forge sends (the effort on the turn, the shortening limit and its instruction), not that Codex keeps its saved prompt or shortens the chat. The measure after the release is the proof. If it shows no gain, the coordinator says so, and the change is small enough to revert alone.
- Codex's shortening step writes a summary with a model, so a detail may be lost. Every repair brief already lists the open findings and the failing checks again, so those cannot be lost. What was tried is the part that depends on the summary.
- Claude's saved prompt after an effort change is outside Forge's control (see above), so the measure reports Claude rounds but this story does not change them.

## For the builders

### Done-when details

1. Source: Forge's run records. Every Codex work run writes a run-start and a run-end event (`repo.record_run`, `src/forge/repo.py` around 550) with `round`, `effort`, `input_tokens` and `cached_input_tokens`. Uncached input is the second minus the third. The coordinator runs the numbers before the first merge of this story and again a week after the release, for work rounds after round 1, grouped by whether the round's effort rose from the round before (the effort ladder, `repo.round_effort`, `src/forge/repo.py` around 606, used in `src/forge/worker.py` around 232) and by family. High-to-high rounds are the control. The reported pair is the median uncached input of the rising rounds before and after, next to the control and the number of rounds in each group. The code part: a run's recorded effort must be the effort the turn really used. Today it comes from the resume reply (`selection` in `src/forge/codex_turn.py`, `selected_request`). Once the effort moves to the turn, the driver sets `selection["effort"]` from it and sends the selection again, so the run-end event still records it. Test: `tests/test_effort_change_keeps_conversation.py` reads the run-end event of a repair round that raised effort and finds the raised effort.
2. In `src/forge/codex_turn.py`, a resumed conversation (`codex.thread_resume(request["thread"], **settings)`) gets its config without `model_reasoning_effort`, and `thread.turn(...)` gets `effort=` with that value (the SDK's `ReasoningEffort`; the pinned SDK 0.171.0 has `Thread.turn(effort=...)`, and its `TurnStartParams.effort` says "for this turn and subsequent turns"). A new conversation keeps the effort in its start config. The nudge turn (`codex.run(... nudge ...)` in `src/forge/worker.py`) takes the same path. `src/forge/codex.py` needs no change: `run()` already puts the effort in the request config, and that file is at the 1,200-line limit, so new lines go in `codex_turn.py`. Tests, with the stand-in Codex server: after a round 1 at low, a repair round at high sends `thread/resume` for the same conversation id with no `model_reasoning_effort` in its config, and sends `turn/start` with effort `high`; a repair round at the same effort still sends the effort on the turn; the first round still sends the effort in `thread/start`. The existing assertions in `tests/test_codex_worker.py` (around 293, the resume config) and `tests/test_codex_resume.py` (`FIX_CONFIG`) change to match. The stand-in server already keeps every request it gets, so the tests read the turn's `effort` from that record.
3. In `src/forge/codex_turn.py`, the driver adds to the thread config of Build, Fix and Lite conversations, on start and on resume: `model_auto_compact_token_limit = 120000` and a `compact_prompt` that tells Codex's summary to keep the open review findings, the failing tests and what was tried. Both keys exist in the pinned Codex 0.171.0 (they are in its binary), but the builder must read Codex's config documentation for what the limit counts (the binary also has `model_auto_compact_token_limit_scope`) and whether `compact_prompt` replaces the whole summary prompt, and word the instruction to fit. Cold reads and reviews do not get it. No new Forge summary tool: the host does the shortening. Tests: a Build conversation's start config and a resumed Fix conversation's config hold the limit and an instruction that names findings, failing tests and what was tried; a cold read's config holds neither. The after-release report also counts, in the turn log, the `contextCompaction` items for conversations that passed the limit (Forge already shows them as "compacting context").

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| EFFORT | A repair round changes effort inside the same conversation | The effort goes on the turn, not on the resume; the run record keeps the effort used | 1, 2 | `src/forge/codex_turn.py` | `tests/test_effort_change_keeps_conversation.py` (new); changed: `tests/test_codex_worker.py`, `tests/test_codex_resume.py` | | no | |
| COMPACT | A long builder conversation is shortened by Codex | The 120K limit and the keep-instruction in every builder conversation's config | 3 | `src/forge/codex_turn.py` | `tests/test_long_builder_chat_is_shortened.py` (new); changed: `tests/test_codex_worker.py`, `tests/test_codex_resume.py` | EFFORT | no | |

New moving parts: none

## Notes

- Evidence for the effort change (25 Nov 2026, run-end events 18 to 25 Nov): Codex low-to-high repair rounds, median 178K uncached input; high-to-high, 74K. Neon kept about 90% cached across low-to-high.
- The skill and the worker brief (`src/forge/templates/skill.md`, `src/forge/templates/brief.md`) need no change: no command, setting or worker step changes.
- Antigravity (`src/forge/antigravity.py`): after `session/resume` it selects the thought level inside the same session. Claude (`src/forge/claude_turn.py`): `ClaudeAgentOptions(effort=..., resume=...)` resumes the same session with the new effort. Both are left as they are.
- Run the cheap repo checks before the round ends: `uv run --frozen --python 3.11 pytest -q tests/test_rules.py::test_4_one_test_per_rule tests/test_rules.py::test_5_forge_stays_small`.
