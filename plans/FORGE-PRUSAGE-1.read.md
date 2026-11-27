---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-27T11:10:33.484171+00:00
seconds: 624.752
read_hash: 61e053a93ed32ac93c0b9cafa43a5b4da717e0b2
round: 2
passed: yes
doc_seen: 61e053a93ed32ac93c0b9cafa43a5b4da717e0b2
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: c440deaf809fd38a490ea25de63b583f27bd4bf9
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21c9e-0c29-7741-adfd-7e0155d4be15
session:
loop_choice:
loop_reason:
---
# Cold read notes

Written by `forge read`. Under every blocking finding, write one disposition line, amend the
doc, then run `forge read <doc>` again until a round has no blocking notes. Notes marked
`Advisory:` are recorded without requiring a disposition or another round:

- `Disposition: cut` when the doc was edited to remove it;
- `Disposition: defer` when the item moved to the spec's Out of scope;
- `Disposition: keep <one-line reason>` otherwise.

A finding inside What counts is cut or deferred. Keep one only when it falls outside that boundary
or is factually wrong or not worth the change, and give as the reason the Leave out line, the
missing Raise line, the cited fact that disproves it, why it is not worth the change, or the
human's `Decided:` line.

Only a genuine trade-off goes to the human, as a question with options.

## Round 1

1. Blocking: Token totals can make the whole pull request record unreadable.
   Raise: Functional  
   Case: normal use - a long build accumulates more than 315,360,000 input tokens. [time_records.py](/src/forge/time_records.py:660) rejects every number above that limit, including the proposed token totals. The current event log already has an item with 303,624,265 build input tokens across 12 runs. A fresh checkout would then lose access to the shared ready record and could be refused a merge.  
   Gain 4, Work 2, Harm 3
   Disposition: cut Token sums are no longer stored in the shared record. They are added up when the block is built, so the 315,360,000 limit on stored numbers never sees them.

2. Blocking: Not done: item 2: plan-read tokens do not reach task pull requests.
   Raise: Not done  
   Case: normal use - a story is read and then built as tasks. [story.py](/src/forge/story.py:349) records the read under the story key, while [time_records.py](/src/forge/time_records.py:198) selects the task’s own events. The plan expressly forbids looking up the story’s runs, so the promised plan-read line is absent.  
   Gain 3, Work 2, Harm 3
   Disposition: cut The promise is narrowed: plan read tokens show only on the pull request of the item that holds the read runs (the story's own record), not on task pull requests. Said in What changes, Done-when 2 and the details.

3. Blocking: Not done: item 2: previously shortened history cannot show its token coverage.
   Raise: Not done  
   Case: normal use - an existing item is upgraded after its earlier history was shortened, then opened on another machine. [time_records.py](/src/forge/time_records.py:851) drops the old events without keeping their run or token counts. The new summary cannot recover those counts, so later reported runs can appear complete while earlier runs are missing. The proposed compaction test covers only history shortened by the new code.  
   Gain 3, Work 2, Harm 3
   Disposition: cut Nothing is stored for shortened history. The block counts only events still in the record and, when the record has a summary, says that earlier models and tokens are not shown. History shortened before this release is covered the same way.

4. Blocking: The spec edit leaves an invalid confirmation.
   Raise: Plan gap  
   Case: normal use - a later story uses the linked cost spec. [item-cost.md](/docs/specs/item-cost.md:4) has a confirmation hash, but the planned body edit does not update its confirmation. [story.py](/src/forge/story.py:975) will no longer recognize it as confirmed, and [records.py](/src/forge/records.py:699) refuses to add its roadmap items.  
   Gain 4, Work 2, Harm 3
   Disposition: cut The spec docs/specs/item-cost.md is no longer edited, so its confirmation stays valid. The task scope, the test and the story text now say so.

5. Blocking: Not done: item 1: the start event can name the requested model rather than the one used.
   Raise: Not done  
   Case: normal use - an Antigravity worker uses its default model or does not support the requested effort. [worker.py](/src/forge/worker.py:824) records the requested values at the start; [antigravity.py](/src/forge/antigravity.py:503) records the actual selection later. Reading only the start can show `default` and the wrong effort.  
   Gain 3, Work 2, Harm 3
   Disposition: cut The model and effort now come from the run end event, which records what ran (Antigravity overwrites them there). A native run, whose end event has no model, uses the start event and shows requested.

6. Blocking: Not done: item 1: shortening history removes earlier builder models.
   Raise: Not done  
   Case: normal use - an item has several rounds and its record grows beyond the history budget. [time_records.py](/src/forge/time_records.py:78) combines older rounds into a line that retains neither their model nor effort. Changing only the individual round line leaves those builders unnamed.  
   Gain 3, Work 2, Harm 3
   Disposition: cut The promise is narrowed: rounds that Forge shortened show no model, and the block says so in one sentence. No model is stored in the folded line.

7. Blocking: Not done: items 1 and 4: the planned changes also alter the board.
   Raise: Not done  
   Case: normal use - an owner opens the board for a built item. [board.py](/src/forge/board.py:639) returns the shared round lines, so changing them adds the model to the board too. Adding `usage` to the shared combined data also exposes that field after compaction, contrary to the promise that the board does not change.  
   Gain 3, Work 2, Harm 3
   Disposition: cut The round line is not changed, so the board does not change. The Build and token lines are made only inside how_it_went. No usage field is added to the shared data or the summary.

8. Blocking: Not done: item 3: the reused exclusions misclassify product and generated files.
   Raise: Not done  
   Case: normal use - product code lives in `src/testimonials/`, or a change includes an unmarked `app.min.js`. [repo.py](/src/forge/repo.py:32) excludes every folder starting with `test`, while its generated-file check only reads Git attributes. [autoreview.py](/src/forge/autoreview.py:35) also recognizes minified files. The size can therefore omit product code or count generated output.  
   Gain 3, Work 2, Harm 3
   Disposition: keep Size reuses the exclusions that close already uses for its 400-line warning. A product folder starting with test or an unmarked minified file is rare and only moves an S, M or L label; a new rule costs more than it saves (AGENTS.md simplicity principles). The plan now says no new rules are added.

9. Blocking: Unproven: item 2: the proposed tests do not prove review totals or wholly unreported runs.
   Raise: Test  
   Case: normal use - a review reports tokens, or every build run is a native run with no token count. The planned tests in [the story](/plans/FORGE-PRUSAGE-1.md:35) assert mixed build coverage only. They can pass if the review line is missing or an all-unreported build shows zero instead of “no tokens recorded.”  
   Gain 3, Work 1, Harm 3
   Disposition: cut Details for item 2 add tests: a review run with tokens shows its line with the sums, and build runs that all have no tokens show no tokens recorded with no zero totals.

10. Advisory: Capacity retries do not create the separate runs the plan assumes.
    Raise: Plan gap  
    Case: rare - Codex retries a turn after a capacity error. [codex.py](/src/forge/codex.py:603) holds one run open across those retries, and [codex_turn.py](/src/forge/codex_turn.py:360) starts the retry inside it. Counting run ends cannot count each retry separately.  
    Gain 2, Work 3, Harm 2
   Disposition: keep - below the bar (follow-up)

11. Advisory: Split: USAGE → model and size, then tokens and cost.
    Raise: Plan gap  
    [The task](/plans/FORGE-PRUSAGE-1.md:46) covers four Done-when items; the read rules require a split above three.  
    Adds work: split the task; F 2 x H 1 = 2; 2 x C = 4  
    Gain 2, Work 1, Harm 1

Skipped `forge next` because it can remove finished worktrees.
   Disposition: keep - below the bar (live with)

## Round 2

12. Advisory: Stopped native builds are omitted from run coverage.
    Raise: Functional  
    Case: normal use - a person stops a native build and starts another. [native.py](/src/forge/native.py:321) records the first run’s start, but cancellation does not record its end. Counting only end events can report complete token coverage while omitting that run.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

13. Advisory: Older retained timing records can contain a builder model that the new line omits.
    Raise: Not done  
    Case: normal use - an item started on an earlier release has an unshortened worker timing but no matching run events. [repo.py](/src/forge/repo.py:462) records model and effort in timings, and [time_records.py](/src/forge/time_records.py:474) already uses those records for round history. The proposed build line reads only events, so it omits that model without the shortened-history warning.  
    Gain 3, Work 3, Harm 2
   Disposition: keep - below the bar (follow-up)

14. Advisory: The new size field reaches the board’s JSON.
    Raise: Not done  
    Case: normal use - an owner reads a ready item with `forge board --json`. Unlike the round text and usage fields addressed in the earlier note, the new `ready.size` field passes through [time_records.py](/src/forge/time_records.py:970) and [board.py](/src/forge/board.py:639). The planned board test checks only for token and cost fields.  
    Gain 3, Work 3, Harm 2
   Disposition: keep - below the bar (follow-up)

15. Advisory: The saved size can be stale when the default branch moves before merge.
    Raise: Functional  
    Case: normal use - another pull request changes the same file after close, and Forge merges and retests the combined change. [merge.py](/src/forge/merge.py:121) can update the head without recalculating size. If the incoming change includes some of the same edits, the saved count no longer describes the delivered diff.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

16. Advisory: The model test does not distinguish requested values from actual values.
    Raise: Test  
    Case: normal use - Antigravity selects a different model or effort from the request. The test in [the story](/plans/FORGE-PRUSAGE-1.md:34) can pass when start and end values match, even if the renderer still reads the start.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

17. Advisory: The size tests do not cover an old ready record without a size.
    Raise: Test  
    Case: normal use - a ready pull request from before the upgrade is refreshed or merged. Existing ready records contain `commit` and `review` but no `size`, as shown in [time_records.py](/src/forge/time_records.py:559). The planned new-record tests can pass even if reading that older record fails.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

18. Advisory: The upgrade description incorrectly says all earlier runs have no recorded tokens.
    Raise: Plan gap  
    [codex.py](/src/forge/codex.py:728) already records token counts, and the current event log contains earlier runs with counts. The proposed aggregation will show those counts when their events remain, contrary to [the story’s upgrade description](/plans/FORGE-PRUSAGE-1.md:11).  
    Gain 2, Work 1, Harm 1

Skipped `forge next` because it can remove finished worktrees.
   Disposition: keep - below the bar (live with)
