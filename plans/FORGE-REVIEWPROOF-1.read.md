---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-26T15:38:42.625433+00:00
seconds: 661.199
read_hash: 3a0b019979e221989408f75e168ecdce5f17832c
round: 1
passed: no
doc_seen: 3a0b019979e221989408f75e168ecdce5f17832c
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21878-4138-7c42-bf9f-92eb0c339e78
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

1. Blocking: Not done: item 1: the proof-list rules still require proof that cannot exist before merge.
   Raise: Not done
   Case: normal use - A Done-when item combines a runtime change with a passing main-branch CI run. [proof.py](/src/forge/proof.py:203) requires an entry, while [review.md](/src/forge/templates/review.md:120) reports a `check:` for runtime behavior, or a test that cannot prove the whole item, as a blocking test finding. The plan changes neither rule for pending proof.
   Gain 4, Work 2, Harm 3
   Disposition: cut Item 1 now says a Done-when item whose proof exists only after the merge uses `check:` in the Proof list (no code change: `proof.py` already accepts `check:`). The worker brief's `check:` rule and the review prompt's `check:` rule (review.md line 122) both name this case, and the reviewer reports it as `After merge:`, not `Test:` or `Not done`. A test closes such an item to Ready.

2. Blocking: Not done: items 1 and 2: a pending check can disappear on the next review.
   Raise: Not done
   Case: normal use - After a repair, the reviewer follows the instruction not to repeat a settled finding. [_settled](/src/forge/review.py:690) carries identities and reasons, not the missing finding, so its check and owner disappear from the new result and pull request. [close.py](/src/forge/close.py:343) also publishes an empty finding list while the new review runs.
   Gain 4, Work 2, Harm 3
   Disposition: cut The carry is now code, not the reviewer's memory: `noise.drop` gets the previous review and adds back any earlier pending check the new result lacks, with its Check and Owner. `score.open_findings` skips pending checks, so `_settled` no longer calls them settled and the reviewer is not told to leave them out. The short `reviewing` block in the pull request is replaced when the result arrives, and the result holds the carried check.

3. Blocking: Not done: item 2: a pending check appears as work to decide at the round limit.
   Raise: Not done
   Case: normal use - A review has a real blocking finding and a pending check scored Harm 5. [review.py](/src/forge/review.py:266) puts every open finding in the owner's decision table; [score.py](/src/forge/score.py:114) scores the pending check as “fix now” without considering its follow-up status. Choosing accept also dismisses every open finding, including that check.
   Gain 4, Work 2, Harm 3
   Disposition: cut `score.open_findings` skips pending checks, so the owner's decision table and the split choice never list them. The accept choice in `close.py` skips them, so accept does not dismiss them and they stay in the pull request. `score.remember` skips them, so they do not enter Known issues. Item 2 has a test for the round limit with one blocking finding and one pending check.

4. Blocking: Not done: item 2: a pending check becomes a new open defect.
   Raise: Not done
   Case: normal use - A pending check points to a changed file. [spotted.py](/src/forge/spotted.py:252) records every P2 or follow-up finding as an open spotted problem. Those records can cause [forge next](/src/forge/nextstep.py:449) to propose a fix, contrary to the plan's statement that the pull request is the record and Forge does not track the check after merge.
   Gain 4, Work 2, Harm 3
   Disposition: cut `spotted.py` skips a pending finding when it records spotted problems (one condition, using `score.pending`), so `forge next` never proposes a fix for it. `spotted.py` is added to PENDING's Scope and the new test checks `plans/spotted.json`.

5. Blocking: Not done: item 3: pull request history still shows a scored P1 as P0.
   Raise: Not done
   Case: normal use - A reviewer gives a finding P1 and Harm 4. [review.py](/src/forge/review.py:1073) records `score.priority`, which turns it into P0, and [time_records.py](/src/forge/time_records.py:498) prints that value in the pull request's “How it went” section. Changing only the four display sites in the plan leaves a false P0 in the same pull request.
   Gain 4, Work 2, Harm 3
   Disposition: cut `review.py` now records the reviewer's own priority in the review-result event (it replaces `score.priority(finding)` on that line, with no new line). `time_records.py` only prints this field in the pull request's "How it went" section, so no change there. The severity test also checks that section for `P1`.

6. Blocking: Plan gap: item 4 does not pin the migration check to the whole change.
   Raise: Plan gap
   Case: normal use - A first round adds a migration, then a repair changes only application code. The existing [review start](/src/forge/review.py:935) is normally the previous reviewed commit, so comparing it with the repaired head misses the migration still present in the branch. The plan names `start` but does not distinguish that repair base from the branch's base; its tests cover only a first review.
   Gain 3, Work 2, Harm 4
   Disposition: cut Item 4 now compares the whole change, not the repair step: `autoreview.migration_floor` diffs the merge base of the default branch and `head` against `head`, so a migration added in round 1 still counts in later rounds. A new test adds a migration in round 1, then repairs only application code, and the finding keeps the floor.

7. Blocking: Not done: item 4: an unrelated new migration raises the score of an old-only finding.
   Raise: Not done
   Case: normal use - A branch adds one migration while a separate finding cites only an older migration. The [planned rule and test](/plans/FORGE-REVIEWPROOF-1.md:44) apply the floor to every matching finding whenever any migration path changes, and explicitly expect Harm 4 for the old-only finding. That conflicts with the promise that an old-only finding keeps the reviewer's score.
   Gain 3, Work 2, Harm 4
   Disposition: cut The owner's rule is about the change, not each finding, and a per-finding match would need more code. The plan now says so: with a migration in the change, every finding that mentions a migration gets the floor; with none, none does. "What changes for you", item 4 of Done when and the test are reworded to match. This is listed under Accepted limits.

8. Blocking: Not done: item 4: the added-work setting can still apply the old migration floor.
   Raise: Not done
   Case: normal use - With `added_work_min_gain = 5`, a Gain 4, Work 2, Harm 1 added-work finding cites an old migration, while the branch changes no migration. [score.py](/src/forge/score.py:98) normalizes that finding again using the planned default of `migration=True`, so the configured minimum does not make it a follow-up and it still blocks.
   Gain 3, Work 2, Harm 4
   Disposition: cut `score.below_added_work_minimum` now calls `normalise` with `migration=False`, because the stored finding already carries the floor that applies to its change. The added-work setting therefore no longer re-applies the old floor. A test in the severity-and-floor file covers `added_work_min_gain = 5` with an old-migration finding on a change with no migration.

9. Blocking: Not done: item 1: prototype fixes do not receive the pending-check instruction.
   Raise: Not done
   Case: normal use - An unsigned prototype fix names a main-branch CI result due after merge. [review.py](/src/forge/review.py:355) uses [review-light.md](/src/forge/templates/review-light.md:10) instead of the planned review prompt; that prompt limits the review to demo, security, data-loss and icon checks. The post-merge check therefore has no planned route into the close output or pull request.
   Gain 3, Work 2, Harm 3
   Disposition: keep `review-light.md` asks only for demo breakage, security and data loss, tells the reviewer not to audit completeness, and never raises `Not done`; the light review also blocks only on P0 (`blocking_level`). So a prototype fix has no post-merge `Not done` finding to convert. A note in the plan records this.

Skipped `forge next` because it can remove finished worktrees.
