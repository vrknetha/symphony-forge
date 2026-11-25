---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-25T05:43:55.100738+00:00
seconds: 594.45
read_hash: eefb602d9052dcfa0bee755555fba71924e815f9
round: 1
passed: no
doc_seen: eefb602d9052dcfa0bee755555fba71924e815f9
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21132-5e37-7533-8ab4-34c5b31dac38
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

1. Blocking: A failed combined test can be bypassed after the suggested retry.
   Raise: Functional. Case: normal use - the default branch moves before a merge, and the combined test fails in a repository whose only CI check is Forge’s review check. [merge.py:137](/src/forge/merge.py:137) has already merged the default branch before the test fails. The planned `forge land` retry closes the item again without that local test and can merge it without a repair.
   Gain 4, Work 2, Harm 3
   Disposition: cut (scope narrowed: close, check and merge next steps stay forge work)

2. Blocking: Cancelled or skipped required checks can produce a retry loop.
   Raise: Functional. Case: normal use - a required check is cancelled or skipped. [worker.py:564](/src/forge/worker.py:564) collects only checks marked `fail`, so [land.py:139](/src/forge/land.py:139) starts no repair. Changing the shared next step to `forge land` makes the same run stop and suggest itself again.
   Gain 4, Work 2, Harm 2
   Disposition: cut (scope narrowed: check next steps unchanged)

3. Blocking: A handed-out repair can exhaust the saved round count and repeat forever.
   Raise: Functional. Case: normal use - a session worker completes a repair, but checks remain red afterward. [worker.py:323](/src/forge/worker.py:323) saves the repair count, and [land.py:87](/src/forge/land.py:87) restores it. Each suggested `forge land` retry then reaches the one-round limit without starting another worker round or the stuck-item check.
   Gain 4, Work 2, Harm 2
   Disposition: cut (scope narrowed: repair next steps unchanged)

4. Blocking: Failed checks on the merge-setting change would direct the owner to merge it.
   Raise: Functional. Case: normal use - the owner enables agent merges and its close encounters a failed check. [merge.py:411](/src/forge/merge.py:411) runs close, so the planned shared check message would suggest `forge land`. [land.py:68](/src/forge/land.py:68) refuses that item and tells the owner to merge its pull request, even though the check failed.
   Gain 4, Work 2, Harm 3
   Disposition: cut (scope narrowed: check next steps unchanged)

5. Blocking: The question instruction conflicts with a request for one build round.
   Raise: Functional. Case: normal use - a person asks for one `forge work` round without closing, and the worker asks a question. The plan says to answer every round question with `forge land --note`, but [land.py:102](/src/forge/land.py:102) then runs the answer, closes the item and can merge it. The plan does not distinguish that request from a question in a full run.
   Gain 4, Work 2, Harm 3
   Disposition: cut (scope narrowed: question next steps unchanged)

6. Blocking: The shipped repository instructions still prescribe the old flow.
   Raise: Not done. Case: normal use - a coordinator reads the instructions installed in a new or upgraded repository. [adapters/AGENTS.md:16](/src/forge/templates/adapters/AGENTS.md:16) says to run `forge work` and then `forge close`, while the shipped [run reference:172](/src/forge/templates/run-reference.md:172) also names `forge work` after failed checks. Neither template is covered by the planned guide changes.
   Gain 4, Work 2, Harm 2
   Disposition: cut (Scope and detail 2 now cover adapters/AGENTS.md; run-reference's status is not one land produces)

7. Blocking: An approved story still needs its first task started before `forge land` can run.
   Raise: Not done. Case: normal use - a story is approved and no task has started. [nextstep.py:769](/src/forge/nextstep.py:769) prints `forge task start`; [land.py:70](/src/forge/land.py:70) requires an existing task checkout. That contradicts the promised next step immediately after approval.
   Gain 4, Work 1, Harm 1
   Disposition: cut (approval keeps forge task start; land comes after the start)

8. Blocking: A session worker does not complete the change in one background run.
   Raise: Not done. Case: normal use - Codex fast mode is enabled, or a Claude session uses a handed-out worker. [land.py:200](/src/forge/land.py:200) ends the run and requires the coordinator to start the worker, hand back its result and run land again. The plan promises one watched run and no coordinator turn between a blocked review and its repair.
   Gain 4, Work 1, Harm 2
   Disposition: cut (Accepted limits now state session-subagent repos keep today's wait)

9. Blocking: The guide test does not prove the promised restriction on notes.
   Raise: Test. Case: normal use - a coordinator consults the guide before giving guidance for a round. The planned test checks only that the skill names `forge land` for building; it can pass while [skill.md:1990](/src/forge/templates/skill.md:1990) still advises adding a note whenever a sentence would help, contrary to Done-when 2.
   Gain 3, Work 1, Harm 1
   Disposition: keep - below the bar (follow-up)
