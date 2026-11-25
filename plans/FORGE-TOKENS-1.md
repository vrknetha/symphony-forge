# Builder briefs send fewer input tokens

2 parts · Risks: none one-way; three accepted limits · New moving parts: none

## What changes for you

- The builder's first brief keeps only what the task needs: its scope paths, its test command, its Done-when, the rules that apply to it, and the proof and commit steps. The shared standards file, the design notes for work that is not a screen, and the release history are named as files the builder opens when it needs them. Screen work keeps its design rules in the brief. (Source: the owner's choice, 25 Nov 2026)
- A repair round still continues the builder's conversation, as today. Its brief now lists the files changed since the last turn, new files included, instead of pasting the full change of up to 200 KB. The new commits, the open findings and the failing checks stay in the brief. (Source: the owner's choice of the split, 25 Nov 2026)
- A long list of related tests in any brief shows its count and the path of a file that holds the full list. The tests the task must run and the names of failing tests stay in the brief. (Source: the owner's choice, 25 Nov 2026)
- After the release, the coordinator compares tokens per merged item with the week before and tells you the measured change. Tokens are shown as uncached input, cached input and output, next to build rounds per item and the share of items that pass their first close.
- The bigger savings come in a second story, "Fewer costly rounds", planned after this one: keep the prompt cache when a repair round changes effort, shorten long conversations, builder self-check against the review rules, one rerun of a flaky CI failure, a stop after two cold reads, a trial of lower review and read effort, and a token budget per item. (Source: the owner's choice of the split, 25 Nov 2026)
- What each repo gets: a new repo and an existing repo get all of this on upgrade to the release that has this story. No setting changes and no command is added.

Design: none (no screen changes)

## Why

Forge is using up its token budget faster than planned. The 93 items that finished from 18 to 25 Nov 2026 used a median of 11.0M input tokens and a mean of 28.5M each. Builds used about 75% of all input, reviews about 19% and cold reads about 6%.

Astra's audit and the advisor's review found the causes. A build turn makes 20 to 46 model calls, and each call reads the whole conversation again, so every token in a brief is paid for many times. Every call also carries about 21k tokens of Codex's own context. The brief inlines the 25.5 KB standards file and design notes even for backend work, and a repair round can paste up to 200 KB of change into the conversation. This story removes those costs quickly; the second story deals with the number of rounds.

## Done when

1. **The builder's first brief names the standards file, the design notes for non-screen work and the release history as files to open, instead of including their text, and screen work keeps its design rules inline.**
2. **A repair round's brief lists the changed files since the last turn instead of their full change, and a related-test list longer than 2,000 characters shows its count and a file path, while required tests and failing test names stay in the brief.**

## Risks

Risks: none one-way. Each part reverts with its pull request.

Accepted limits:
- A builder may skip a standard that is now a file reference. If review findings or rounds per item rise after the release, the coordinator says so and the rule moves back into the brief.
- A repair builder sees file names, not the change itself, so it may open some files again. It made those changes itself earlier in the same conversation.
- Builders and cold readers that run as native subagents of the coordinating session (Claude or Codex) record no token counts today. The measure covers only runs that Forge starts through the Codex app server, and the report states the share of native runs in each week, so a shift to native runs cannot look like a saving.

## For the builders

### Done-when details

1. `src/forge/worker.py` brief assembly (around 660-760) stops inlining the standards file, `PRODUCT.md`/`DESIGN.md` for non-UI kinds and the release-history part of `src/forge/templates/brief.md`; it names their paths with one line on when to read each. UI work keeps the design notes inline. The brief keeps the scope paths and the test step it has today. Test: a backend fix's brief names the standards path and has none of its text; a UI task's brief still holds the design notes.
2. `_changes` in `src/forge/worker.py` (around 516-542) always gives `git diff --cached --name-status` against the turn's start instead of the full diff; the commit list stays. The related-test list (`_existing_tests`, around 774): over 2,000 characters, write the full list to a file in the item's thread folder and put its count and path in the brief; required tests and failing check names stay inline. Failing checks keep the log tail and named failure report they carry today (`_failing`); this story adds no new failure detail. Tests: a repair brief after a change lists the changed and new file names and holds no diff text; a long test list gives the count and path; a short list stays inline.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| BRIEF | The first brief keeps only what the task needs | The brief names standards, non-UI design notes and release history as files | 1 | `src/forge/worker.py`, `src/forge/templates/brief.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_brief_names_reference_files.py` (new) | | no | |
| RESUME | Repair briefs list changed files; long test lists go to a file | File names instead of diffs in repair briefs; count and path for long test lists | 2 | `src/forge/worker.py` | `tests/test_repair_brief_lists_changed_files.py` (new); changed: `tests/test_codex_resume.py`, `tests/test_fix_every_fix_round_resends_the_whole_worker.py` | BRIEF | no | |

New moving parts: none

## Notes

- Baseline (18 to 25 Nov 2026, run-end events, counted after the accounting fix): 93 finished items, median 11.0M input tokens, mean 28.5M; 3.4 build runs and 3.3 review runs per item. Earlier records undercount 241 of 750 medium runs; do not use them.
- Second story, "Fewer costly rounds" (to plan after this one, from Astra's answer of 25 Nov 2026): cache-safe effort change and compaction above about 120k of current context (needs a source for assertion details); builder self-check against the review rules; one rerun of a flaky CI failure on the same commit; two cold reads stop automatic reading; separate blind Terra high-versus-max replays for review and read effort (pass only with every confirmed critical defect found, no extra false blocks and at least 20% less input); a per-item token budget that offers split, accept or continue. The owner's switch of this repo's Sol builds to high effort waits until this story is measured.
- 25 Nov 2026: the owner removed the Codex host-context part (HOST). Codex's built-in skills (about 600 tokens) and memory guidance stay: the cut is small, the prompt is cached, and a live proof needs an API key secret the repo does not have.
