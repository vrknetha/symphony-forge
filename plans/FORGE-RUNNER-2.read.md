---
reader: antigravity (default)
read_at: 2026-11-28T10:14:20.304902+00:00
seconds: 67.523
read_hash: f8300013efb054a5fc205b3ea1a88a3fb380ef5c
round: 1
passed: no
doc_seen: f8300013efb054a5fc205b3ea1a88a3fb380ef5c
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation:
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

1. Blocking: `STAY` contradicts `tests/test_runner_stops_one_item_and_tells_the_owner.py` and the end-of-run summary notice.
   Raise: Plan gap
   Case: normal use - a current stopped or parked item remains open while the runner is active
   Done-when detail 2 says a stopped or parked item counts as unfinished while it is current so the runner stays on until the owner answers, while Done-when detail 4 says `tests/test_runner_stops_one_item_and_tells_the_owner.py` keeps passing and `STAY`'s Tests cell omits it. In `tests/test_runner_stops_one_item_and_tells_the_owner.py:88`, `:137`, and `:164`, the test waits for `_runner_exited(tmp_path)` while current stopped/parked items (`review-fix`, `ask-fix`, `size-fix`) are still open, and lines `:100-103` and `:150-158` assert that `stops.summary` sends a `"Forge runner done"` notice listing those waiting items. Pin whether `STAY` updates that test and drops the waiting-items summary while the runner stays on, or changes the exit rule.
   Gain 4, Work 2, Harm 2
   Disposition: fix - a stop that waits on the owner no longer keeps the runner on; the end summary and its test stay unchanged (For the builders, detail 2).

2. Advisory: `WAIT` asks `wait_for_stop` to print `_notice_body` and `Next:`, but `runner.json` does not store `code` or `lines`.
   Raise: Plan gap
   Case: normal use - a human-merge wait or refusal stop appears while `forge next --wait` is running
   Done-when detail 5 says `wait_for_stop(top)` in `src/forge/stops.py` polls local records and prints `_notice_body` and `Next:`, while Done-when detail 6 says `runner.json` format does not change. In `src/forge/stops.py:110-147`, `_notice_body(top, item, code, lines)` only reconstructs worker questions and review-limit stops from disk; human-merge waits (`:123-126`) and refusals (`:127-147`) read `lines` from the `forge land` child process, which `stops.ended` (`src/forge/stops.py:169-179`) does not save. Pin how `wait_for_stop` gets the notice and `Next:` line for those stops (for example via `nextstep._item`).
   Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)

3. Advisory: `ANSWER` checks `forge next` for a trailing `Next:` line, but `forge next` prints the whole repo ending in `Builds running: N of M`.
   Raise: Plan gap
   Done-when detail 3 says `stops.try_answer(top, item)` runs only when `forge next` for that item ends with `Next: forge work <item> --note "<answer>"`. In `src/forge/nextstep.py:26-30` and `:389-391`, `forge next` takes no item argument and ends with `Builds running: N of M`; pin calling `nextstep._item` (or matching that `Next:` line for `item`) instead.
   Gain 2, Work 1, Harm 1
   Disposition: keep - below the bar (live with)
