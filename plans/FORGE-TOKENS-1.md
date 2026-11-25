# Builder rounds send fewer input tokens

3 parts · Risks: none one-way; three accepted limits · New moving parts: none

## What changes for you

- A repair round no longer continues the builder's long conversation. It starts a new conversation with a short brief that holds the assignment, the open review findings, the failing tests and their failure lines, the branch's commits so far and what the earlier rounds tried. The first model call of a repair round drops from a median of about 170k input tokens to about the size of a first-round brief. This reverses the rule of 16 Nov 2026 that a repair round continues the same builder. (Source: the owner's choice, 25 Nov 2026)
- The builder's brief keeps only what the task needs: its scope, its Done-when, the rules that apply to it, and the proof and commit steps. The shared standards file, the design notes for work that is not a screen, and the release history are named as files the builder opens when it needs them. (Source: the owner's choice, 25 Nov 2026)
- Codex runs that Forge starts (builds, reviews, cold reads) leave out Codex's own memory guidance and its list of host skills, where Codex's settings allow it. These add about 21k tokens to every model call today. Forge's own rules and skills stay. (Source: the advisor's review, 25 Nov 2026)
- A long list of related tests in the brief shows its count and the path of a file that holds the full list. The tests the task must run and the names of failing tests stay in the brief. (Source: the owner's choice, 25 Nov 2026)
- After the release, the coordinator compares tokens per merged item with the week before and tells you the measured change. Tokens are shown as uncached input, cached input and output, next to build rounds per item and the share of items that pass their first close.
- What each repo gets: a new repo and an existing repo get all of this on upgrade to the release that has this story. No setting changes and no command is added.

Design: none (no screen changes)

## Why

Forge is using up its token budget faster than planned. From 18 to 25 Nov 2026 a merged item used a median of 13.2M input tokens and a mean of 30.0M. The 10% largest items used 44% of the total. Builds used about 75% of all input, reviews about 19% and cold reads about 6%.

Astra's audit and the advisor's review found the causes. A build turn makes 20 to 46 model calls, and each call reads the whole conversation again. Items average 3.4 build rounds, and rounds 2 and later use 78% of build input, because each repair round continues a conversation that only grows. Every call also carries about 21k tokens of Codex's own context. The brief inlines the 25.5 KB standards file and design notes even for backend work.

## Done when

1. **A repair round starts a new builder conversation with a short brief that holds the assignment, open findings, failing tests, the branch's commits and what was tried, instead of continuing the old conversation.**
2. **The builder's brief names the standards file, the design notes for non-screen work and the release history as files to open, instead of including their text.**
3. **Codex builds, reviews and cold reads that Forge starts run without Codex's memory guidance and host skill list where Codex's settings allow it.**
4. **A related-test list longer than 2,000 characters shows its count and a file path, while required tests and failing test names stay in the brief.**

## Risks

Risks: none one-way. Each part reverts with its pull request.

Accepted limits:
- A new conversation does not remember the earlier attempts in detail. The short brief lists the commits and what was tried, so the builder does not repeat a failed attempt, but some files get read again.
- A builder may skip a standard that is now a file reference. If review findings or rounds per item rise after the release, the coordinator says so and the rule moves back into the brief.
- Claude builders that run as native subagents record no token counts today, so the measure covers Codex runs only.

## For the builders

### Done-when details

1. The fresh brief already exists (`src/forge/worker.py:306-309`, `fresh_brief`); a repair round uses it instead of the continued brief, extended with: the branch's commit subjects since the start of the item, the open blocking findings, the failing test names with their failure lines, and a short "tried so far" section built from earlier rounds' handback reports. The repair round's effort ladder stays as it is (low first, top after a verified failure). Tests: a repair round after a blocked review starts a new Codex thread (no `thread/resume`), and its brief holds the findings, failing tests and commit list. Existing tests that assert a repair continues the same thread (for example `tests/test_effort_ladder.py::test_1_a_failed_round_runs_at_top_effort_in_the_same_thread`) change to the new rule; FORGE-ANTIGRAVITY-1's `tests/test_antigravity_build.py::test_2` changes the same way if that part has merged.
2. `src/forge/worker.py` brief assembly (around 707-760) stops inlining the standards file, `PRODUCT.md`/`DESIGN.md` for non-UI kinds and the release-history part of `src/forge/templates/brief.md`; it names their paths with one line on when to read each. UI work keeps the design notes inline. Test: a backend fix's brief names the standards path and has none of its text; a UI task's brief still holds the design notes.
3. Forge's Codex request config (`QUIET` in `src/forge/codex.py:64`, applied at `:589`) adds the Codex settings that turn off memory guidance and the host skill list for Forge's runs. Check the exact keys in the pinned Codex SDK's config schema first; if a key does not exist, leave that part out and record the reason in the commit. Test: the request Forge sends to the stub app server carries the keys.
4. `src/forge/worker.py` related-test list (around 774): over 2,000 characters, write the full list to a file in the item's thread folder and put its count and path in the brief; required tests and failure names stay inline. Test: a long list gives the count and path; a short list stays inline.

## Tasks

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| FRESH | Repair rounds start fresh with a short brief; the brief keeps only what the task needs | Repair rounds use the fresh brief plus commits, findings, failing tests and tried-so-far; the brief names standards, non-UI design notes and release history as files | 1, 2 | `src/forge/worker.py`, `src/forge/templates/brief.md`, `src/forge/codex_turn.py`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md` | `tests/test_repair_round_starts_fresh.py` (new), `tests/test_brief_names_reference_files.py` (new); changed: `tests/test_effort_ladder.py` | | no | |
| HOST | Codex runs leave out host memory and skill list | The Codex request config keys for Forge's runs | 3 | `src/forge/codex.py` | `tests/test_codex_runs_skip_host_context.py` (new) | | no | |
| TESTLIST | Long related-test lists go to a file | Count and path in the brief for long lists | 4 | `src/forge/worker.py` | `tests/test_long_test_list_goes_to_a_file.py` (new) | FRESH | no | |

## Notes

- Baseline (18 to 25 Nov 2026, run-end events, counted after the accounting fix): median 13.2M input tokens per merged item, mean 30.0M; 3.4 build runs and 3.3 review runs per item. Earlier records undercount 241 of 750 medium runs; do not use them.
- After this story: look at why items need 3.4 rounds, and at review and cold-read effort (Terra max). The owner's switch of this repo's Sol builds to high effort waits until this story is measured.
