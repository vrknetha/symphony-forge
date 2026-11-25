# Cold reads stop churning after round one

2 parts · Risks: none one-way · New moving parts: none

## What changes for you

- A cold read note labelled `Advisory:` never holds a plan, whatever its scores. Today a scored advisory note holds like a blocking one, although the read instructions say it needs no other round. (Source: the owner's choice, 25 Nov 2026)
- From round 2, a note holds only when it has Harm 4 or 5, or when it says an earlier note is not fixed. Other new notes in later rounds stay recorded in the read notes, but they do not start another round. (Source: the owner's choice, 25 Nov 2026)
- A cold read note scored Gain 3 and Harm 3 no longer holds on that score alone, and a note whose own case says it is rare does not hold unless its Harm is 4 or 5. Code reviews keep today's bar. (Source: the owner's choice, 25 Nov 2026)
- Answering a note may only narrow the plan. When the fix would add something new (a table, a column, a flow, a sign-in or a question to the person), the agent records the note as deferred or asks you, instead of writing it into the plan. Advisory notes are not written into the plan. (Source: the owner's choice, 25 Nov 2026)
- At the round limit, Forge no longer asks you to choose one more round, split or accept. It writes the open notes into the plan's Notes, which every builder of the story receives, as required checks, each with a test, marks them kept, and the plan goes on to approval. Specs and decisions get the same list in their Notes. A note at Harm 4 or 5 in the last round still gets one more round first, unless the round before also had one, as today. (Source: the owner's choice, 25 Nov 2026)
- What each repo gets: a new repo and an existing repo get all of this on upgrade to the release that has this story. A read already stopped at the round limit before the upgrade still accepts the owner's choice. No setting changes and no command is added.

Design: none (no screen changes)

## Why

Eight long cold reads in a client repo ran 46 rounds, about 276M tokens. Round 1 found real defects, such as a plan that let an unchanged suggested group be published publicly. Later rounds were mostly problems that the previous round's fixes had created: in the longest read, about 17 of the 29 blocking notes in rounds 2 to 10 came from such fixes, and some fixes added new features. 235 of 277 notes (85%) were held, 61 of them only through the Gain 3 and Harm 3 route, and 11 held notes were rated rare by the reader itself. Scored advisory notes kept loops running with no blocking note at all.

## Done when

1. **A note labelled `Advisory:` never holds a cold read, and from round 2 only a note with Harm 4 or 5, or one that says an earlier note is not fixed, holds it.**
2. **A cold read note scored Gain 3 and Harm 3 with no other reason to hold, or one whose case says it is rare with Harm below 4, does not hold, while code review findings keep today's bar.**
3. **At the cold read round limit, the open notes are written into the document's Notes as required checks with tests and marked kept, and Forge asks the owner nothing.**
4. **The read instructions, the coordinator guide and the worker brief say that answering a note may only narrow the plan, that additions become a deferral or an owner choice, and that advisory notes are not written into the plan.**

## Risks

Risks: none one-way. Each part reverts with its pull request.

Accepted limits:
- A real defect raised as advisory, or raised new in round 2 with Harm 3, no longer stops the plan. It still reaches the builders, and the code review checks the code.
- Some fixable gaps that held before (Gain 3 and Harm 3) move to the code review.
- At the round limit, nobody chooses a split; open notes go to the builders even when they would fit better in a separate story.

## For the builders

### Done-when details

1. `src/forge/score.py` `note_holds` (:148): a note whose label is `Advisory:` returns False before scoring. The round rule lives where the round is known: `src/forge/story.py` `passed` (:725-736), `stopped` (:738), `undisposed` (:756) and `read_result` (:393) count a note from round 2 on only when its Harm is 4 or more or its title starts with `Not fixed <n>:` or `Disputed keep <n>:`. Add one helper in story.py for "this read note holds in this round" and use it in those places. `score.notes` (:69) never gives a below-bar keep to a `Not fixed` or `Disputed keep` note. `src/forge/templates/cold-read.md` (:273-293) requires the `Not fixed <n>:` title prefix (after `Blocking:`) for a note that says an earlier note's answer did not fix it. Tests: an all-advisory round 2 passes with no disposition; a round-2 Harm 3 note does not hold; a round-2 Harm 4 note and a `Not fixed 3:` note with Harm 2 hold and are not auto-kept.
2. Add a read-only bar in `score.py` for read notes: the same as `bar` except Gain 3 with Harm 3 is `follow-up`, and a note whose `Case:` line says rare (the existing `RARE`) or whose `Adds work:` line contains `F 1 x` anywhere is rare, but only when its Harm is below 4 (a Harm 4 or 5 note holds by the existing rule). `bar` itself stays for code review (`holds`, :130). Tests: a Gain 3, Work 1, Harm 3 read note does not hold; the same scores on a review finding still hold; `Adds work: protect branch ownership; F 1 x H 3 ...` does not hold; the same line on a Harm 4 data-loss note holds.
3. Both places that stop at the limit change: `story.read` (:197) and `read_result` (:431). Instead of refusing with `read_loop`, append each open note to the document's `## Notes` section (create the section at the end when missing; this covers story plans, specs and decisions) under `Required checks from the cold read:`, one line per note with its title, its case and "add a test that proves it"; give each a `Disposition: keep - builder check at the round limit`; set `loop_choice = "accept"` with that reason; store `read_hash`; commit; print `Next: forge next`. Story workers already receive the plan's Notes (`src/forge/worker.py:610`), so the checks reach every builder. The code review treats these checks as required, not accepted: `src/forge/review.py` (:630) leaves notes with `keep - builder check at the round limit` out of the accepted list, and `src/forge/templates/review.md` (:266) says a missing check or test from `Required checks from the cold read:` in the plan's Notes is `Not done`. The P0 extra round in `stopped` stays as it is. `--resolve` stays accepted whenever the record's round is at or past the limit with no `loop_choice`, so a read stopped before the upgrade can still be resolved even when the new rule would pass it. Remove the `read_loop` refusal and `read_question` if nothing else uses them. Update any cold-read limit wording that `worker.py` injects (near :27) and the `forge read` listing (`story.py:1197`). Update `tests/` that pin the owner question at the limit (search for `read_loop` and `--resolve`). Tests: a story read that ends round 2 with open notes writes them to Notes, marks them kept, and shows as waiting for approval; a spec read does the same in its Notes; a record stopped under the old rule still accepts `--resolve accept`.
4. `src/forge/templates/cold-read.md` (the label line at :58 and the disposition list at :304-317), `src/forge/templates/skill.md` (:1733 and the read-limit text near the `forge read` row), `src/forge/templates/brief.md` (:789): advisory notes never hold and are not written into the plan; a disposition `cut` may only remove or narrow plan text; a fix that would add a table, column, flow, sign-in or question becomes `defer` or an owner question; the round limit writes open notes as builder checks. Each task updates the guide text for its own behaviour in the same change (review rule). Run `forge sync` for `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md`. Test: the shipped skill and cold-read template state the narrow-only rule.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| RULES | Fewer read notes hold; answers may only narrow | Read hold rules, the stricter read bar, the narrow-only rule and their guide text | 1, 2, 4 | `src/forge/score.py`, `src/forge/story.py`, `src/forge/templates/cold-read.md`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_read_notes_hold_less.py` (new) | | no | |
| LIMIT | The round limit turns open notes into builder checks | Automatic builder checks at the limit and its guide text | 3 | `src/forge/story.py`, `src/forge/worker.py`, `src/forge/review.py`, `src/forge/templates/review.md`, `src/forge/templates/cold-read.md`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_read_limit_writes_builder_checks.py` (new); changed: tests that pin the owner question at the read limit | RULES | no | |

New moving parts: none

## Notes

- Evidence: audit of 8 long client cold reads and 10 two-round reads, 25 Nov 2026 (no client named here). Correlation only, not used in this plan: the long reads ran on Terra and the short ones on Sol.
- Measure after the release: cold read rounds per story and read tokens per story against the weeks before.
