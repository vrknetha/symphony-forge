# Land is the default way to run each change

1 part · Risks: none one-way · New moving parts: none

## What changes for you

- When a task or fix has just started and its builder has not run yet, the next step Forge prints is `forge land <item>`, run in the background. Today it is `forge work <item>`, and the agent then runs `forge close` by hand and starts each repair round itself. `forge land` already builds, closes, sends review findings and failed checks back to the builder and merges in one run, so a blocked review goes straight to the next repair round instead of waiting for the agent's next turn. After a story is approved, the next step stays `forge task start`, and its next step is then `forge land`. (Source: the owner's choice, 25 Nov 2026)
- `forge land` still stops where a person decides today: at the round limit, when an item is stuck, and when a round asks a question. The next steps Forge prints at those stops do not change. In a repo where a person merges, land stops at Ready and asks the person to merge, as it does today.
- The Forge guide and the repo instructions that Forge ships say to run each item with `forge land` in the background after it starts, and to use `forge work` and `forge close` only when a person asks for one build round or one close.
- What each repo gets: a new repo and an existing repo get the new next step and guide text on upgrade to the release that has this story. No setting changes and no command is added.

Design: none (no screen changes)

## Why

From 18 to 25 Nov 2026, a blocked review waited a median of 3.8 minutes, and one in four waited 20 minutes or more, before its repair round started (143 cases in this repo). The wait is the coordinating agent's turn: Forge prints `forge work` as the first step, so the agent runs build and close as separate commands and starts each repair by hand. `forge land` already runs the whole loop. Faster links between agent programs were also weighed and judged not worth their cost, because the wait is the agent's turn, not message delivery.

## Done when

1. **When a task or fix has started and its builder has not run, the next step that task start, fix start and forge next print is `forge land <item>`.**
2. **The coordinator guide and the repo instructions that Forge ships tell coordinators to run each started item with `forge land` in the background, and keep `forge work` and `forge close` for a person's request for one round or one close.**

## Risks

Risks: none one-way. The part reverts with its pull request.

Accepted limits:
- A coordinator no longer gets a turn between repair rounds to add guidance. Rounds that stop for a person (round limit, stuck, question) still give that turn, and `forge work` stays available.
- Where the builder runs as the coordinating session's own subagent (a Claude-only repo, or Codex fast mode), land still stops at each round for the session to run the subagent and hand back. Those repos keep today's wait; the change helps repos whose builders Forge starts itself.
- Next steps printed after a close, a check failure or a merge stop stay `forge work`, because they can come from a person's own close and some of them must not loop through land.

## For the builders

### Done-when details

1. `src/forge/task.py` (task start at :521, fix start at :835) and `src/forge/nextstep.py` (the `started` status at :52; keep the builder-name suffix at :1148-1149 working for the new step) name `forge land {item}`. Nothing else changes: the next steps in `close.py`, `checks.py`, `merge.py`, `native.py`, `worker.py` and the other `nextstep.py` states stay as they are (cold read round 1, findings 1-5). Tests: task start, fix start and forge next for a started item each print `Next: forge land <item>`.
2. `src/forge/templates/skill.md` (the "Build it" row at :182 and the flow text), `src/forge/templates/adapters/AGENTS.md` (flow steps 3-4 at :16-18) name `forge land <item>` in the background after the start; `forge work` and `forge close` stay in the table for one round or one close. The note paragraph at skill.md :1990 says a note goes with `forge land <item> --note` when a land run stopped for a person, and with `forge work` only for a single requested round. `run-reference.md` :172 describes a status that land does not produce and stays. Run `forge sync` so `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` and this repo's AGENTS.md block follow. Test: the shipped skill and AGENTS.md template name `forge land` for building a started item.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| NEXT | The start step and the guide name forge land | Next step after a start, guide and repo instructions | 1, 2 | `src/forge/task.py`, `src/forge/nextstep.py`, `src/forge/templates/skill.md`, `src/forge/templates/adapters/AGENTS.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `AGENTS.md` | `tests/test_next_step_names_land.py` (new); changed: existing tests that assert `Next: forge work` after a start | | no | |

New moving parts: none

## Notes

- Measure after the release: the gap from a blocked review to the next build start, per item, against the 18 to 25 Nov baseline (median 3.8 min, 75th percentile 20 min, 143 cases).
