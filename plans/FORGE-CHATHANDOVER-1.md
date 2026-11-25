# Hand a long coordinator chat over to a fresh chat

1 part · Risks: none one-way · New moving parts: none

## What changes for you

- When you ask the coordinator to hand over, or after its chat has been compacted once, it refreshes Forge's existing handoff note on demand, adds its open decisions and lessons there, and tells you to clear the chat. The note holds the items in flight, their state, what each waits on and the exact next commands, all from `forge next`.
- A new or cleared chat in a Forge repo shows one line at its start that names the handoff note and its date, so the fresh chat reads the note first instead of the old conversation.
- No new command and no second file: the coordinator runs the session-end note's own step on demand.
- What each repo gets: a new repo gets this at setup, and an existing repo gets it on upgrade to the release that has this story. No setting changes.

Design: none (no screen changes)

## Why

A long coordinator chat reads the whole conversation again on every tool call. The owner reports that one client used about 593 million Claude tokens in one day. Forge already writes a handoff note before each compaction, but nothing tells the coordinator to write it on demand, and a fresh chat does not know the note exists unless the coordinator guide is loaded.

## Done when

1. **When the owner asks for a hand over, or after a compaction, the coordinator guide tells the coordinator to refresh the handoff note with the existing step, add its decisions and lessons, and tell the owner to clear the chat.**
2. **A new or cleared chat in a Forge repo with a handoff note starts with one line that names the note and its date; a repo with no note shows no such line.**

## Risks

Risks: none one-way. The part reverts with its pull request.

Accepted limits:
- The note's current state is what `forge next` reports. Background runs that the old chat started outside Forge (its own shell jobs) are not listed; the coordinator adds their log paths under Decisions and lessons when it writes the note.

## For the builders

### Done-when details

1. `src/forge/templates/skill.md`, section `## Handoff` (around line 623): add that on the owner's request or after a compaction the coordinator runs `forge hook handoff`, adds one line per open decision, lesson and outside log path under `## Decisions and lessons` in `.git/forge/handoff.md`, then tells the owner in one plain line to clear the chat (Claude `/clear`, Codex a new chat). Run `forge sync` so `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md` match. No test: guide text.
2. `context_hook` in `src/forge/nextstep.py` (around line 195): when `repo.forge_dir(top) / "handoff.md"` exists, print one line naming its path and the date from its `## Current state (<date>)` heading. Keep the hook offline and short. Test (new, runs the forge command): after `forge hook handoff` in a new repo, `forge hook context` prints the line with today's date; without the file it prints no such line.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| HANDOVER | Hand over on demand and point a fresh chat at the note | Guide step for an on-demand hand over; a start-of-chat line naming the note | 1, 2 | `src/forge/nextstep.py`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_context_hook_names_handoff_note.py` (new) | | no | |

New moving parts: none

## Notes

- 25 Nov 2026: a Sippo ask; the owner wants it. The intake draft asked for a new command; this plan reuses `forge hook handoff` instead, because Forge keeps a fixed ceiling on commands and the step already does the work.
