# Hand a long coordinator chat over to a fresh chat

1 part · Risks: none one-way · New moving parts: none

## What changes for you

- Forge tells the coordinator how full its chat is. When the chat uses more than half of its context window, a hook shows the coordinator one line with the real token count and the window size. Claude's window is about 1M tokens, so this is about 500K; Codex and Antigravity use about 500K, so about 250K. (Source: the owner's choice, 25 Nov 2026)
- At the next quiet moment (after a merge or while it waits for checks), the coordinator refreshes Forge's existing handoff note, adds its open decisions and lessons, and tells you in one line to clear the chat. You can also ask for a handover at any time.
- The guide's current rule "hand over at 20 to 30%, never past 40%" changes to "more than half, at a quiet moment", because a chat starts at about 7 to 10% already. (Source: the owner's choice, 25 Nov 2026)
- A new or cleared chat in a Forge repo starts with one line: read the handoff note at its path, from its date, then run `forge next`. The fresh chat continues from that note instead of the old conversation.
- No new command and no second file: the coordinator runs the existing handoff step on demand.
- What each repo gets: a new repo gets this at setup, and an existing repo gets it on upgrade to the release that has this story. No setting changes.

Design: none (no screen changes; the only new text is two short lines in the agent's chat)

## Why

A long coordinator chat reads the whole conversation again on every tool call. The owner reports that one client used about 593 million Claude tokens in one day. At Opus 5.5's cache-read price of about $0.20 per million tokens, a call at 500K tokens costs about five times a call at 100K. Forge already writes a handoff note before each compaction, but the coordinator cannot see how full its chat is, so it does not know when to hand over, and a fresh chat does not know the note exists unless the coordinator guide is loaded.

## Done when

1. **When a coordinator chat uses more than half of its context window, a hook shows the coordinator one line with the token count and the window size; below half it shows nothing.**
2. **The coordinator guide says to hand over at the next quiet moment after that line, or when the owner asks: refresh the handoff note with the existing step, add decisions, lessons and the log paths of its own background jobs, and tell the owner to clear the chat.**
3. **A new or cleared chat in a Forge repo with a handoff note starts with one line that names the note's full path and date and says to read it, then run `forge next`; a repo with no note shows no such line.**

## Risks

Risks: none one-way. The part reverts with its pull request.

Accepted limits:
- The note is built offline from what `forge next` reports, without GitHub's scheduled-run alerts. The fresh chat runs `forge next`, which shows them.
- A host that gives no token count to its hooks gets no context line; the guide rule and the owner's request still work there.

## For the builders

### Done-when details

1. No new hook entry: the existing `PreToolUse` Bash hook (`deny` in `HOSTS`, `src/forge/githooks.py`) also runs the check, because the coordinator runs nearly every step through Bash; approval recording on `PostToolUse` stays as it is. Put the check in a new module (for example `src/forge/contextsize.py`): `nextstep.py` is at 1,197 of 1,200 lines. The line reaches the agent only as structured context, never as plain output: Claude `hookSpecificOutput.additionalContext`, Codex the same field per its hook docs, merged with whatever the deny hook already returns, and always with `hookEventName: "PreToolUse"`, which both hosts require. A missing, null or unreadable transcript path gives no line and never blocks the command.
   - Size, Claude: the last assistant message's `usage` in the hook input's `transcript_path`: input + cache read + cache creation + output tokens. Window: what the host reports; otherwise 1,000,000 (every current Claude model, Haiku 5.5 included).
   - Size, Codex: the last `token_count` event's latest-request usage (not the session total), against its `model_context_window`.
   - Only the coordinator: no line when the hook input names a subagent (`agent_id`) or when `FORGE_WORKER=1` is set (Forge sets it for every builder run, `src/forge/claude_turn.py`, `src/forge/codex.py`). A coordinator working in a task or fix worktree still gets the line.
   - Once per chat: keep the last warned tenth per `session_id` in a small file under `repo.forge_dir(top)`. Warn first past half, then once at each further 10% of the window.
   - No count found: no line.
   - Line, for example: "This chat uses 520K of 1M tokens. Hand over at the next quiet moment: see Handoff in the Forge guide."
   - Tests (new, run the forge command): a Claude transcript at 60% (output tokens counted) gets the context field; one at 40% gets none; a second call by the same chat at the same size gets none, while a different chat at 60% gets it; the output carries `hookEventName: "PreToolUse"`; a Codex rollout whose latest request is at 60% of its window gets it, and one whose session total is past half but whose latest request is at 30% gets none; a call with `FORGE_WORKER=1` or from a subagent gets none, while a coordinator call from a task worktree gets it; a null transcript path gets no line and the command is allowed.
2. `src/forge/templates/skill.md`: in `## Waiting or stopped runs`, replace "20 to 30% ... Never go past 40%" with "more than half of the context window, at a quiet moment". In `## Handoff`, add the fresh-chat steps: run `forge hook handoff`, add one line per open decision, lesson and background-job log path under `## Decisions and lessons` in the note, then tell the owner in one plain line to clear the chat (Claude `/clear`, Codex a new chat). Say to add a background job's log path to the note when the job starts, not later. Rename `## Hand over` to "Hand over to another machine or person", and change the `## Handoff` sentence "At hand over, copy its settled notes to `docs/handover.md`" to apply only to that section, so a fresh chat on the same machine writes no second file. Run `forge sync` for `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md`. Test: extend `tests/test_fix_client_repos_lose_the_agent_s_state_the.py` to check that the synced guide has the half-window rule and the clear-the-chat step.
3. `context_hook` in `src/forge/nextstep.py`: when `repo.forge_dir(top) / "handoff.md"` exists, print "Read the handoff note <absolute path> from <date> first, then run forge next.", with the date from its `## Current state (<date>)` heading. `handoff_hook` reads the old notes again just before it replaces the file, so a coordinator line added while the report ran is kept. Test (new, runs the forge command): after `forge hook handoff` in a new repo, `forge hook context` run from a linked task worktree prints the absolute shared path and today's date; without the file it prints no such line.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| HANDOVER | Tell the coordinator when to hand over and point a fresh chat at the note | A half-window context line, the guide steps and a start-of-chat line naming the note | 1, 2, 3 | `src/forge/nextstep.py`, `src/forge/contextsize.py` (new), `src/forge/deny.py`, `src/forge/githooks.py`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `.claude/settings.json`, `.codex/hooks.json` | `tests/test_context_hook_names_handoff_note.py` (new), `tests/test_context_line_past_half_window.py` (new); changed: `tests/test_fix_client_repos_lose_the_agent_s_state_the.py` | | no | |

New moving parts: none

## Notes

- 25 Nov 2026: a Sippo ask; the owner wants it. The intake draft asked for a new command; this plan reuses `forge hook handoff` instead, because Forge keeps a fixed ceiling on commands and the step already does the work.
- 25 Nov 2026, owner: 20 to 30% is too little, because a chat starts at 7 to 10%; hand over when idle and over 50 to 60%. The coordinator recommended 300K tokens for all hosts; the owner chose more than half of each chat's window.
- Window sizes and prices (third-party pages, Nov 2026): Claude Opus 5.5 and Sonnet 5.5 1M, cache read $0.20 and $0.10 per million; GPT-6.2 Sol 1.05M by API, 500K default in Codex, cache read $0.10, 2x price above 272K with an API key; Gemini 4 Neon 1M by API, 512K in Antigravity, cache read $0.15.
