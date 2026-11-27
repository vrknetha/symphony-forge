# Show model use and change size in pull requests

1 part · Risks: none · New moving parts: none

## What changes for you

- Each task or fix pull request already has a "How it went" block. It now also names the model and effort that built the work, next to the rounds, new review findings and time it already shows. (Source: the owner's design, 27 Nov 2026)
- The block shows the tokens Forge recorded, with build, review and plan read apart: input tokens, how many of them came from cache, and output tokens. When some runs recorded no tokens, it says so, for example "2 of 3 runs reported tokens". (Source: the owner's design, 27 Nov 2026)
- When the work is ready, the block shows the size of the change that was delivered: S, M or L, with the lines and files behind it. S is up to 100 lines added plus removed, M is up to 400 and L is above 400. Tests, docs and generated files do not count. A change with only tests or docs says "no product lines". (Source: the owner's design, 27 Nov 2026)
- The block shows no money. It says "cost unavailable". Forge does not record how a run is billed, so it cannot say "on subscription" yet. This narrows the earlier cost spec, which planned price tables and board columns; that spec is updated in this story. (Source: the owner's design, 27 Nov 2026)
- What each repo gets: a new repo gets this in the pull request of its first build. An existing repo gets it from its next build after it upgrades to the release that has this story. Runs that happened before the upgrade have no recorded tokens, and the block says so. No setting changes and no command is added. The board, the reports and the `forge next` messages do not change.

Design: none (no screen changes)

## Why

An owner who wants to compare builders on similar work cannot do it today. The pull request shows rounds, findings and time, but not which model built the work, how many tokens it used, or how big the change was. Without size, a long build of a large change looks like a slow builder. Without the count of runs that reported tokens, a low total can be a gap in the records. The numbers go in the pull request only, where the owner already reads the build's history. This story does not compare builders for the owner and does not give a verdict.

## Done when

1. **A task or fix pull request's "How it went" block names the builder model and effort beside the rounds, the new review findings and the time it already shows.**
2. **The block shows input, cached input and output tokens for build, review and plan read, each apart. Each run counts once, including retries. When some runs recorded no tokens it says "N of M runs reported tokens", and these counts stay after Forge shortens old history.**
3. **When the work is ready, the block shows S, M or L with the lines (added plus removed) and the number of product files, or "no product lines" for a change with only docs or tests.**
4. **The block says "cost unavailable" and shows no dollar amount. This story adds no board column, report, `forge next` message or split rule.**

## Risks

Risks: none

## For the builders

### Done-when details

1. The builder model and effort come from the item's worker `run start` events (`kind` `work` or `worker`), which already carry `model` and `effort` (`src/forge/worker.py:916`, `src/forge/codex.py:604`). In `src/forge/time_records.py` line 483 the step text is `built at <effort>`; change it to `built at <effort> on <model>` and keep the `requested` suffix. Three tests assert the `built at <effort>` text (`tests/test_effort_records.py:78`, `:97`, `tests/test_round_seconds.py:165`), so the new text must keep that start. When the run has no model, print the old text. Rounds, new findings and time are not touched. Update the sentence about `built at <effort>` in `src/forge/templates/skill.md` (line 2123) and the two synced copies. Test (new `tests/test_pr_usage_summary.py`, run through `forge close` on a new repo, as `tests/test_effort_records.py` and `tests/test_item_time_history.py` do): a fix with a worker run start that has model and effort gives a pull request body whose round line contains `built at low on <model>`.
2. Tokens come from the `run end` events (`repo.record_run`, `src/forge/repo.py:550`). Each run has one `run end` keyed by `run_id`, so counting by `run_id` counts each run once; a review retry and a Codex capacity retry are separate runs, and a Codex turn that continues adds its tokens inside its one run (`codex.py:731`). Add one function to `time_records.py` that reads the events and returns, for each of build (`work`, `worker`), review (`review`) and plan read (`read`): the number of runs, the number of runs whose end has an integer `input_tokens`, and the sums of `input_tokens`, `cached_input_tokens` and `output_tokens`. A run that recorded no tokens (a native in-chat subagent, an old record) adds nothing to the sums and counts only in the run total. Render one line per kind that has runs, for example `Build tokens: input 120,000 (cached 90,000), output 4,000; 2 of 3 runs reported tokens`. Leave out "N of M" when all runs reported, and say "no tokens recorded" when none did. Tests and CI runs (`test`, `ci`) are not shown. Plan read runs are recorded under the story key (`src/forge/story.py:994`), so a task or fix pull request shows a plan read line only when its own item has read runs; do not add a new lookup for the story's runs.
   Compaction: `_summarised` (around line 803 to 877) moves old events into the summary and drops them. Make it add the function's counts for the events it moves to a `usage` field of the summary, and make the render add the summary's `usage` to the counts of the events that remain. Add `usage` to the fields the summary keeps (the `kept` tuple at line 870 and `_summed`), and fold two summaries by adding counts. Counts only, so the record stays inside `RECORD_BUDGET`. Tests (same new file): a fix with three build runs, two with tokens and one without, shows `2 of 3`; a repeated close does not count a run twice; with the record budget forced small (as `tests/test_item_time_history.py` case 1 does for compaction) the token lines and the "N of M" counts are the same before and after the old rounds are folded.
3. Size reuses the calculation in `close.py` (lines 240 to 252: the `git diff --numstat` against the review base, excluding `review.DOC_EXCLUDES` and `repo.TEST_PATHS`, minus `repo.generated_files`). It runs only for task items now (`if "/" in item`), so a fix gets no size; the calculation must run for a fix too, while the "aim for about 400" warning stays for parts only. To keep `close.py` from growing (it has 1,165 lines; the limit is 1,200), move the calculation into a function in `time_records.py` that returns `(lines, files)`, where files counts the rows that are not generated, and call it from close. Close keeps the result in the `ready` record it writes before it publishes the pull request (`close.py:521`, add a `size` entry), and `how_it_went` copies it into `data["ready"]` next to `commit`, `review` and `base` (line 561), which already survives compaction (`ready` is in `base`, line 596). The block shows `Size: S (60 lines in 3 files)`; S is at most 100 lines, M at most 400, L above 400; zero lines shows `Size: no product lines`. A block with no ready record (a blocked close, an old pull request) shows no size line and no guess. Tests (same new file): a fix that adds 30 lines of product code shows `S (30 lines in 1 file)`; a fix that adds only a test file or only a doc shows `no product lines`; a change of 101 product lines shows `M`; a change of 401 shows `L`; a task shows the same line.
4. The cost line is the fixed text `Cost: unavailable` ("cost unavailable" is the owner's wording; use it as the owner wrote it). Forge records no billing basis today (nothing in `src/forge` names a plan login or an API key), so "on subscription" cannot be shown yet; do not add a field only for it. No dollar amount, price table, board column, `forge board --json` field, report, `forge next` message or split rule is added. Update `docs/specs/item-cost.md` in this change: add a short "Narrowed on 27 Nov 2026" note near the top of Behaviour that says items 3 to 5 and acceptance criteria 3 and 4 (price table, estimated cost, board columns) are not built in this version, and that the pull request shows tokens, coverage, size and "cost unavailable" instead. Do not rewrite the rest of the spec. Test (same new file): the body has the cost line, no `$` followed by a digit, and `forge board --json` has no token or cost field for the item.

## Tasks

<!-- One row per task. The plan is one part: it changes one block of one file and its record, so one part proves all four items. -->

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| USAGE | Model use and change size in How it went | Builder model and effort, token lines with coverage, change size and "cost unavailable" in the pull request block, with counts kept through compaction | 1, 2, 3, 4 | `src/forge/time_records.py`, `src/forge/close.py`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `docs/specs/item-cost.md` | `tests/test_pr_usage_summary.py` (new) | | no | |

New moving parts: none

## Notes

- Size: about 100 to 150 changed lines with the test. Item 2's compaction part is the riskiest piece; if the builder finds it needs far more than about 40 lines, it should stop and say so, not add a second record format.
- Module sizes (the limit is 1,200 lines, `test_5_forge_stays_small`): `close.py` is 1,165 lines and must not grow, which is why the size calculation moves to `time_records.py` (1,050 lines).
- Review rule (a change to what a coordinator or worker sees updates the skill): the round line text changes, so `templates/skill.md` and its two synced copies change. The worker brief does not change.
- What each repo gets, for review: new repo and existing repo both get the new block from the first build after they have this release. Per the review rules the test runs on a new repo only; the suite's upgrade test is not extended, because no record is converted. Old runs keep no tokens, and the block says "no tokens recorded".
- Guesses to confirm with the owner. (1) "On subscription when known" is not built: no run records its billing basis, so the line always says "cost unavailable". If the owner wants "on subscription" now, Forge first needs to record the sign-in type of each run, which is a separate change. (2) The size line shows only when close has marked the work ready, because the size is stored in the ready record; a blocked close shows no size. (3) A fix now gets its size too, because the old calculation ran only for parts. (4) Plan read tokens show only on the pull request of the item that has plan read runs, in practice the story's own record, not its task pull requests. (5) "Product files" counts the files left after the existing test, docs and generated-file exclusions.
- Out of scope, as the owner decided on 27 Nov 2026: dollar estimates, a price table, board columns, reports, `forge next` notices, split rules, a pre-build size grade, and any comparison or verdict between models.
