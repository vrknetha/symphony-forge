# Land is the default way to run each change

1 part · Risks: none one-way · New moving parts: none

## What changes for you

- After a task or fix starts, after a story is approved, and after a review, the checks or the tests block a change, the next step Forge prints is `forge land <item>`, run in the background. Today it is `forge work <item>`, and the agent then runs `forge close` by hand. `forge land` already builds, closes, sends findings back to the builder and merges in one run, so a blocked review goes straight to the next repair round instead of waiting for the agent's next turn. (Source: the owner's choice, 25 Nov 2026)
- `forge land` still stops where a person decides today: at the round limit, when an item is stuck, and when a round asks a question. Only then does the agent add a note with `forge land <item> --note "<text>"`. In a repo where a person merges, land stops at Ready and asks the person to merge, as it does today.
- The Forge guide that coordinators read says to run each item with `forge land` in the background, and to use `forge work` only when a person asks for one build round without closing.
- What each repo gets: a new repo and an existing repo get the new next steps and guide text on upgrade to the release that has this story. No setting changes and no command is added.

Design: none (no screen changes)

## Why

From 18 to 25 Nov 2026, a blocked review waited a median of 3.8 minutes, and one in four waited 20 minutes or more, before its repair round started (143 cases in this repo). The wait is the coordinating agent's turn: Forge prints `forge work` as the next step, so the agent runs build and close as separate commands and starts each repair by hand. `forge land` already runs the whole loop. Faster links between agent programs were also weighed and judged not worth their cost, because the wait is the agent's turn, not message delivery.

## Done when

1. **After a task or fix starts, a story is approved, or a close stops on a blocking review, failed checks or failed tests, the next step Forge prints is `forge land <item>`, and a question from a round names `forge land <item> --note "<answer>"`.**
2. **The coordinator guide that Forge ships tells coordinators to run each item with `forge land` in the background and to add a note only on a round that stopped.**

## Risks

Risks: none one-way. The part reverts with its pull request.

Accepted limits:
- A coordinator that wants to add guidance before every repair round no longer gets a turn between rounds. Rounds that stop for a person (round limit, stuck, question) still give that turn, and `forge work` stays available.
- `forge land` runs longer than one build round, so the agent watches one long background run per item instead of several short ones.

## For the builders

### Done-when details

1. Change the next-step text from `forge work {item}` to `forge land {item}` where the step is "build or repair this item": `src/forge/task.py` (task start at :521, fix start at :835, the "already started" refusal at :28), `src/forge/nextstep.py` (the `started`, `fixing` and `checks failed` states at :52-57 and the stopped-worker line near :1111; keep its builder-name suffix at :1148 working for the new step), `src/forge/close.py` (the blocked-review step at :51 keeps its `--dismiss` alternative; the recorded-choice lines at :61, :164, :173; the question step at :71), `src/forge/checks.py:27`, `src/forge/merge.py:31`, `src/forge/native.py:367`. Leave as `forge work` the steps that tell the agent to merge the default branch first (close.py :34, :38, :826; task.py :740, :855-858) and the upgrade and review-skip steps. Check that land, which runs these commands in-process, does not print a nested "Next: forge land" that loops: land's own stop messages win. Tests: one test per entry point named in Done-when 1 (task start, fix start, an approved story's first task, a blocked close, failed checks, a round's question) reads the printed next step.
2. `src/forge/templates/skill.md`: the "Build it" row (:182) and the flow text name `forge land <item>` in the background; `forge work` stays for "build one round without closing". Update the worker brief only if it names the coordinator's next command. Mirror into `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md` through `forge sync`. Test: the shipped skill names `forge land` for building an item.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| NEXT | Next steps and the guide name forge land | Next-step text and coordinator guide | 1, 2 | `src/forge/task.py`, `src/forge/nextstep.py`, `src/forge/close.py`, `src/forge/checks.py`, `src/forge/merge.py`, `src/forge/native.py`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_next_step_names_land.py` (new); changed: existing tests that assert `Next: forge work` for these steps | | no | |

New moving parts: none

## Notes

- Measure after the release: the gap from a blocked review to the next build start, per item, against the 18 to 25 Nov baseline (median 3.8 min, 75th percentile 20 min, 143 cases).
