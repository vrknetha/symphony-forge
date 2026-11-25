# Cold reads stop churning after round one

3 parts · Risks: none one-way · New moving parts: none

## What changes for you

- A cold read note labelled `Advisory:` never holds a plan, whatever its scores. Today a scored advisory note holds like a blocking one, although the read instructions say it needs no other round. (Source: the owner's choice, 25 Nov 2026)
- From round 2, a note holds only when it has Harm 4 or 5, or when it says an earlier note is not fixed. Other new notes in later rounds are recorded and reach the builders, but they do not start another round. (Source: the owner's choice, 25 Nov 2026)
- A cold read note scored Gain 3 and Harm 3 no longer holds on that score alone, and a note whose own case says it is rare does not hold. Code reviews keep today's bar. (Source: the owner's choice, 25 Nov 2026)
- Answering a note may only narrow the plan. When the fix would add something new (a table, a column, a flow, a sign-in or a question to the person), the agent records the note as deferred or asks you, instead of writing it into the plan. Advisory notes are not written into the plan. (Source: the owner's choice, 25 Nov 2026)
- At the round limit, Forge no longer asks you to choose one more round, split or accept. It writes the open notes into the plan's builder section as required checks, each with a test, marks them kept, and the plan goes on to approval. A note at Harm 4 or 5 that is new in the last round still gets one more round first, as today. (Source: the owner's choice, 25 Nov 2026)
- What each repo gets: a new repo and an existing repo get all of this on upgrade to the release that has this story. A read already stopped at the round limit before the upgrade still waits for the owner's choice. No setting changes and no command is added.

Design: none (no screen changes)

## Why

Eight long cold reads in a client repo ran 46 rounds, about 276M tokens. Round 1 found real defects, such as a plan that let an unchanged suggested group be published publicly. Later rounds were mostly problems that the previous round's fixes had created: in the longest read, about 17 of the 29 blocking notes in rounds 2 to 10 came from such fixes, and some fixes added new features. 235 of 277 notes (85%) were held, 61 of them only through the Gain 3 and Harm 3 route, and 11 held notes were rated rare by the reader itself. Scored advisory notes kept loops running with no blocking note at all.

## Done when

1. **A note labelled `Advisory:` never holds a cold read, and from round 2 only a note with Harm 4 or 5, or one that says an earlier note is not fixed, holds it.**
2. **A cold read note scored Gain 3 and Harm 3 with no other reason to hold, or one whose case says it is rare, does not hold, while code review findings keep today's bar.**
3. **At the cold read round limit, the open notes are written into the plan's builder section as required checks with tests and marked kept, and Forge asks the owner nothing.**
4. **The read instructions, the coordinator guide and the worker brief say that answering a note may only narrow the plan, that additions become a deferral or an owner choice, and that advisory notes are not written into the plan.**

## Risks

Risks: none one-way. Each part reverts with its pull request.

Accepted limits:
- A real defect raised as advisory, or raised new in round 2 with Harm 3, no longer stops the plan. It still reaches the builders, and the code review checks the code.
- Some fixable gaps that held before (Gain 3 and Harm 3) move to the code review.
- At the round limit, nobody chooses a split; open notes go to the builders even when they would fit better in a separate story.

## For the builders

### Done-when details

1. `src/forge/score.py` `note_holds` (:148): a note whose label is `Advisory:` returns False before scoring. The round rule lives where the round is known: `src/forge/story.py` `passed` (:725-736), `stopped` (:738) and `undisposed` (:756) count a note from round 2 on only when its Harm is 4 or more or its title starts with `Not fixed` or `Disputed keep` (the earlier-note labels in `src/forge/templates/cold-read.md:273,293`). Add one helper in story.py for "this read note holds in this round" and use it in those three places. Tests: an all-advisory round 2 passes with no disposition; a round-2 Harm 3 note does not hold; a round-2 Harm 4 note and a `Not fixed` note hold.
2. Add a read-only bar in `score.py` for read notes: the same as `bar` except Gain 3 with Harm 3 is `follow-up`, and a note whose `Case:` line says rare (the existing `RARE`) or whose `Adds work:` line starts with `F 1` is rare. `bar` itself stays for code review (`holds`, :130). Tests: a Gain 3, Work 1, Harm 3 read note does not hold; the same scores on a review finding still hold; an `F 1 x H 3` added-work note does not hold.
3. `story.read` (:197): when `stopped` is true, instead of refusing with `read_loop`, append each open note to the plan below `## For the builders` under `### Required checks from the cold read`, one line per note with its title, its case and "add a test that proves it", then give each a `Disposition: keep - builder check at the round limit`, set `loop_choice = "accept"` with that reason, store `read_hash`, commit, and print `Next: forge next`. The P0 extra round in `stopped` stays. A notes file whose record already holds a stop from before the upgrade (round at the limit and no `loop_choice`) still accepts `--resolve`. Remove the `read_loop` refusal and its question builder if nothing else uses them. Update `tests/` that pin the owner question at the limit to the new behaviour (search for `read_loop` and `--resolve`). Test: a read that ends round 2 with open notes writes them as required checks, marks them kept, and the plan shows as waiting for approval.
4. `src/forge/templates/cold-read.md` (the label line at :58 and the disposition list at :304-317), `src/forge/templates/skill.md` (:1733 and the read-limit text near the `forge read` row), `src/forge/templates/brief.md` (:789): one rule: advisory notes never hold and are not written into the plan; a disposition `cut` may only remove or narrow plan text; a fix that would add a table, column, flow, sign-in or question becomes `defer` or an owner question; the round limit writes open notes as builder checks. Update the `forge read` listing in `story.py:1197` to match. Run `forge sync` for `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md`. Test: the shipped skill and cold-read template state the narrow-only rule.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| BAR | Advisory and later-round notes stop holding; a stricter bar for read notes | Read hold rules in score and story | 1, 2 | `src/forge/score.py`, `src/forge/story.py` | `tests/test_read_notes_hold_less.py` (new) | | no | |
| LIMIT | The round limit turns open notes into builder checks | Automatic builder checks at the limit | 3 | `src/forge/story.py` | `tests/test_read_limit_writes_builder_checks.py` (new); changed: tests that pin the owner question at the read limit | BAR | no | |
| GUIDE | Answers may only narrow the plan | Read instructions, guide and brief text | 4 | `src/forge/templates/cold-read.md`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_read_answers_only_narrow.py` (new) | LIMIT | no | |

New moving parts: none

## Notes

- Evidence: audit of 8 long client cold reads and 10 two-round reads, 25 Nov 2026 (no client named here). Correlation only, not used in this plan: the long reads ran on Terra and the short ones on Sol.
- Measure after the release: cold read rounds per story and read tokens per story against the weeks before.
