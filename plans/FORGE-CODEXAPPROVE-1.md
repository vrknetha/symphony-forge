# Approve a story from a Codex chat

1 part · Risks: none one-way · New moving parts: none

## What changes for you

- In a Codex chat, the coordinator shows the story and then asks you to type one line, for example `approve FORGE-X-1 3f9a2c`. When you type it, Forge records your approval. You do not need Plan mode. (Source: the owner's choice, 26 Nov 2026)
- The short code at the end belongs to the exact text you were shown. If the story changed after it was shown, Forge records nothing and says so, and the coordinator shows the new text with a new code.
- Only a line that you type counts. Forge reads it from your own message, which an agent cannot write, so the same human-only check as in Claude chats still holds.
- Claude chats keep Plan mode approval as today. A Codex chat that is already in Plan mode can still approve through the question, as today.
- What each repo gets: a new repo gets this at setup, and an existing repo gets it on upgrade to the release that has this story. No setting changes.

Design: none (no screen changes; one line in the chat)

## Why

Forge tells a Codex coordinator to ask the approval question with Codex's question tool, but Codex offers that tool only in its Plan mode, and the agent cannot switch to Plan mode itself. So no story can be approved from a Codex chat, and an owner who coordinates with Codex is stuck at every story.

## Done when

1. **In a Codex chat, when the owner types `approve <KEY> <code>` with the code Forge gave for the shown story, Forge records the approval of that story.**
2. **A typed line whose code does not match the story's current text, a line that comes from anything other than the owner's own message, or a story that is not waiting for approval records nothing and says why.**
3. **The coordinator guide and `forge next` tell a Codex coordinator to show the story and ask the owner to type that line.**

## Risks

Risks: none one-way. The part reverts with its pull request.

Accepted limits:
- As with Plan mode today, Forge cannot prove that the owner read the story before typing the line.

## For the builders

### Done-when details

1. Add a `UserPromptSubmit` entry for Codex in `HOSTS` (`src/forge/githooks.py`) that runs `forge hook approval`. In `src/forge/approval.py`, a `UserPromptSubmit` payload whose prompt is exactly `approve <KEY> <code>` (trimmed, case-insensitive key) approves through the existing `_approve` checks: the story waits for approval, its read is clean, the code is the first 6 hex characters of the same section digest that `approve_plan_<digest>` uses today, replay refusal keyed on the session id and the prompt's event id. Any other prompt records nothing and prints nothing. Run `forge sync` so `.codex/hooks.json` matches. Test (new, runs the forge command): a UserPromptSubmit payload with the right line records the approval; `forge next` then shows the story approved.
2. Refusals reuse `REFUSALS` (`no_match` for a code that does not match, `replay` for a second use). A tool payload (PostToolUse, PreToolUse) carrying the same text records nothing. Tests: wrong code refused with the no_match message; the same line twice records once; a PostToolUse payload with the line records nothing.
3. Codex's `Next:` line in `src/forge/nextstep.py` (today: request_user_input with id approve_plan_…) becomes: show the doc down to `## For the builders`, then ask the owner to type `approve <KEY> <code>`. Update the Plan Mode approval paragraph in `src/forge/templates/skill.md` for Codex and run `forge sync` for the guide copies. Test: `forge next` with tools = codex prints the typed line with the right code.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| TYPED | Typed approval in Codex chats | The owner approves a story from a Codex chat by typing one line | 1, 2, 3 | `src/forge/approval.py`, `src/forge/githooks.py`, `src/forge/nextstep.py`, `src/forge/templates/skill.md`, `.codex/hooks.json`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_codex_typed_approval.py` (new) | | no | |

New moving parts: none

## Notes

- 26 Nov 2026: the owner reported that plans cannot be approved from a Codex chat. The owner chose typed approval over asking the owner to switch to Plan mode.
