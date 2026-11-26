# Approve a story from a Codex chat

1 part · Risks: none one-way · New moving parts: none

## What changes for you

- In a Codex chat, the coordinator shows the story and then asks you to type one line, for example `approve FORGE-X-1 3f9a2c`. When you type it, Forge records your approval. You do not need Plan mode. (Source: the owner's choice, 26 Nov 2026)
- The short code at the end belongs to the part you approve ("What changes for you" and "Done when") as it was shown, and only to the story named in the line. If that part changed after it was shown, Forge records nothing and says so, and the coordinator shows the new text with a new code. A change to the other parts of the story does not change the code, as in Plan mode.
- Only a line that you type counts. Forge reads it from your own message and ignores a message that a helper agent sends, so the same human-only check as in Claude chats still holds.
- Claude chats keep Plan mode approval as today. A Codex chat that is already in Plan mode can still approve through the question, as today.
- What each repo gets: a new repo gets this at setup, and an existing repo gets it on upgrade to the release that has this story. In Codex you trust the new hook once (the coordinator tells you how). No setting changes.

Design: none (no screen changes; the flow is: the coordinator shows the story, asks you to type the line, you type it, and Forge confirms or says why it recorded nothing)

## Why

Forge tells a Codex coordinator to ask the approval question with Codex's question tool, but Codex offers that tool only in its Plan mode, and the agent cannot switch to Plan mode itself. So no story can be approved from a Codex chat, and an owner who coordinates with Codex is stuck at every story.

## Done when

1. **In a Codex chat, when the owner types `approve <KEY> <code>` with the code Forge gave for that story's shown text, Forge records the approval of that story.**
2. **A typed line records nothing and says why when its code does not match the named story's current approved text, when it is an approval line typed wrongly (for example a short code), when it comes from anything other than the owner's own message, or when the named story is not waiting for approval. Other messages are left alone.**
3. **The coordinator guide and `forge next` tell a Codex coordinator to show the story and ask the owner to type that line.**

## Risks

Risks: none one-way. The part reverts with its pull request.

Accepted limits:
- As with Plan mode today, Forge cannot prove that the owner read the story before typing the line.

## For the builders

### Done-when details

Names: `approval.hook` in `src/forge/approval.py` and `HOSTS` in `src/forge/githooks.py`. A typed approval reuses the checks of `_approve` (the story waits for approval, its read is clean, design and sign-off checks, the recording and the push). Split `_approve` so those steps take the story and the event id from the caller, and the question and Plan Mode paths keep their digest lookup unchanged.

1. Add `"UserPromptSubmit": (None, "approval")` to the `.codex/hooks.json` entry of `HOSTS`. In `approval.hook`, a payload whose `hook_event_name` is `UserPromptSubmit` goes to a new typed path before the tool-name test (a prompt payload has no `tool_name`). The line is `approve <KEY> <code>`: trimmed, `approve` and the key in any letter case, then exactly 6 hex characters. The code is the first 6 characters of the digest that `waiting_digest` returns for the named story only (look the key up in each checkout with `story.stories_here`, as `_approve` does), so another waiting story's code never approves it. The replay marker uses the payload's `session_id` and `turn_id` as session and event (a Codex prompt payload carries no tool event id); a missing one refuses with `no_identity`. The hook also records nothing for a message from a helper agent: before building, read Codex 0.172's real `UserPromptSubmit` payload for a spawned helper's message and refuse on the field that marks it (the test uses a captured helper payload). If Codex gives no such mark, stop and tell the coordinator, since the owner text above depends on it. Run `forge sync` so `.codex/hooks.json` matches. Test (new, runs the forge command): a UserPromptSubmit payload with the right line records the approval; `forge next` then shows the story approved.
2. A message that is not an approval line (does not start with `approve` and a word shaped like a story key) records nothing and prints nothing. A message that starts that way but is not `approve <KEY> <6 hex>` (short, long or non-hex code, extra words) prints one reason line (new `REFUSALS` entry `bad_line`: it must read `approve <KEY> <6-character code>`) and records nothing. A real refusal on this path (`no_match` for a wrong code, an unknown key or a story not waiting; `replay` for a second use in the same turn; `no_identity`) must not stop the owner's message: catch the `Refused`, write it with `last_refusal`, print the reason to stdout and exit 0, because the launcher turns any non-zero exit into exit 2 and Codex then blocks the prompt. The coordinator sees that stdout and shows the new text with its new code. A tool payload (PostToolUse, PreToolUse) carrying the same text records nothing. Tests: wrong code for the named story prints the `no_match` reason and exits 0; with two stories waiting, story A's key with story B's code records neither; the right key and code records only that story; a 5-character code and a non-hex code print the `bad_line` reason; "approve the plan please" and an ordinary prompt print nothing; the same line twice in one turn records once; a PostToolUse payload with the line records nothing.
3. Codex's `Next:` line in `src/forge/nextstep.py` keeps the Plan mode question and puts the typed line first: show the doc down to `## For the builders`, then ask the owner to type `approve <KEY> <code>` (the first 6 hex characters of the digest); a Codex chat already in Plan mode may instead ask `request_user_input` with the unchanged id, question, header and choices, so the question handler in `approval.py` is untouched. Add to that guidance: after the owner types the line, run `forge next`; if the story still waits and no reason is shown, the hook did not run, so ask the owner to review and trust the new hook in Codex with `/hooks` (Codex skips a new hook until it is trusted, and Forge trusts only the hooks of the threads it starts), and check that the installed Forge is the release this repo pins (a teammate's older Forge ignores the line without a word). Update the Plan Mode approval paragraph in `src/forge/templates/skill.md` and the line in `src/forge/templates/adapters/AGENTS.md` that says a story is approved through Plan Mode and no other step exists, then run `forge sync` for `AGENTS.md` and the skill copies; update the Codex sentence in `docs/guide.md` and add the typed path to `docs/specs/plan-approval.md`. Tests: `forge next` with tools = codex prints the typed line with the right code and still prints the question id; update the Codex assertion in `tests/test_shortplan_docs.py` (`then ask request_user_input`) and the hook count in `tests/test_setup.py`; `tests/test_approval.py` and `tests/test_contracts.py` keep passing on the unchanged question path.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| TYPED | Typed approval in Codex chats | The owner approves a story from a Codex chat by typing one line | 1, 2, 3 | `src/forge/approval.py`, `src/forge/githooks.py`, `src/forge/nextstep.py`, `src/forge/templates/skill.md`, `src/forge/templates/adapters/AGENTS.md`, `AGENTS.md`, `docs/guide.md`, `docs/specs/plan-approval.md`, `.codex/hooks.json`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_codex_typed_approval.py` (new), `tests/test_shortplan_docs.py`, `tests/test_setup.py`, `tests/test_approval.py`, `tests/test_contracts.py` | | no | |

New moving parts: none

## Notes

- Decided (26 Nov 2026): the owner chose a 6-character code, the first 6 hex of the existing digest. An agent that grinds the plan text for a matching code is not normal use, and a changed plan still needs a clean read first.
- User-facing is no because no screen changes: that flag brings screen design and rendered checks, and there is no screen to check. The flow is in the Design line above.
- 26 Nov 2026: the owner reported that plans cannot be approved from a Codex chat. The owner chose typed approval over asking the owner to switch to Plan mode.
