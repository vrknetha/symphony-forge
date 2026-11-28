---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-28T04:19:35.189016+00:00
seconds: 771.797
read_hash: 2df142a23a885aedf87a061c00ef7ff94b23cb77
round: 2
passed: no
doc_seen: 2df142a23a885aedf87a061c00ef7ff94b23cb77
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: da38c2ea19414b4769c7bf4cd24da1002837ba81
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a2200f-0b99-7012-9a49-21297d4d5e18
session:
loop_choice: accept
loop_reason: Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details
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

1. Blocking: Not done: close cannot check a newly run test with the evidence supplied to the reviewer.  
   Raise: Not done  
   Case: normal use - a part reaches its first close with a must-prove test. [close.py](/src/forge/close.py:357) starts tests alongside review, so the prompt says they are running; [proof.py](/src/forge/proof.py:423) has no result unless a matching result was already cached. CI results also arrive after review. The reviewer cannot establish the pass required by the plan.  
   Gain 5, Work 3, Harm 3
   Disposition: cut - the plan now proves a named test through the commit's Proof list and `proof.check`, which close runs after the test run; the reviewer only judges whether it exercises the behaviour.

2. Blocking: Not done: skipping the model review also skips every plan check.  
   Raise: Not done  
   Case: normal use - a person uses the supported `--no-review` option on a part with a must-prove note. The plan relies on the reviewer to report both unmet checks and after-merge checks, but [close.py](/src/forge/close.py:366) creates an empty finding list when review is skipped. The pull request can therefore omit an after-merge check and its owner, or proceed without checking proof.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `proof.check` runs with `--no-review`, and close adds the after-merge entries itself to every result, so a skipped review omits nothing.

3. Blocking: Not done: read-limit notes are assigned to parts that cannot prove them.  
   Raise: Not done  
   Case: normal use - an open note concerns a screen built by a later part, while an earlier part owns the schema. [The plan](/plans/FORGE-THINREVIEW-1.md:71) assigns the note to `all`, and its record rules make every part prove it. The earlier part cannot test code that the later part has yet to build; the later part may wait for the earlier one to merge, as [task.py](/src/forge/task.py:483) shows.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `all` now means the leaf parts, which can see earlier parts' work, and a leaf may answer `not reachable in this part - <why>`.

4. Blocking: Not done: a newly reported unmet plan check can become a follow-up in a repair review.  
   Raise: Not done  
   Case: normal use - the first review finds a P0, and the second finds that a must-prove check is unmet. [autoreview.py](/src/forge/autoreview.py:19) marks a new non-P0 finding as a repair follow-up; [review.py](/src/forge/review.py:1115) then skips the required-item classification. The plan explicitly keeps that repair rule while requiring plan checks to hold at any score.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `repair_findings` now exempts `Not done: Plan check` titles, so a new unmet check holds in a repair review.

5. Blocking: Not done: a passing second read can still fail the approval gate.  
   Raise: Not done  
   Case: normal use - round two reports a new Gain 4, Work 1, Harm 3 note. The proposed round-two rule makes it nonblocking, but [score.py](/src/forge/score.py:71) does not add a disposition for that score, and [story.py](/src/forge/story.py:770) checks dispositions without the round. The proposed gate test covers an automatically disposed note, not this passing note.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `undisposed`, the approval gate and `check_pr_docs` now use the same per-round hold rule, and a test covers a round-two Harm 3 note with no disposition.

6. Blocking: Unproven: an open plan-read stop may disappear on upgrade.  
   Raise: Test  
   Case: normal use - an existing read is stopped at round two on a Gain 4, Work 1, Harm 3 note. [story.py](/src/forge/story.py:752) derives the stop from the current blocking rule; under the proposed rule that note no longer holds in round two. The plan does not pin how to recognize that pre-upgrade stop, and its upgrade test checks a `close` stop rather than a read stop.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - a pre-upgrade stopped read is judged again by the new rule (passes, or gets the limit step), its recorded choice is kept, and test 6 covers it.

7. Blocking: Not done: splitting a stopped P0 or required finding does not release the part.  
   Raise: Not done  
   Case: normal use - the owner chooses `split` after the new two-round stop. [close.py](/src/forge/close.py:132) marks the finding as a follow-up, but [score.py](/src/forge/score.py:132) still holds a P0, and [review.py](/src/forge/review.py:188) still holds a required finding. The next worker round receives the supposedly split finding again.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `score.holds` and `review.blocking` now stop holding a finding whose follow-up starts with `Split into`; a test covers a split P0 stop.

8. Blocking: Not done: the automatic extra-round policy conflicts with the new limit.  
   Raise: Not done  
   Case: normal use - an existing repo has `auto_more_round = true` and a functional P1 remains at the limit. The plan says both to turn every such ordinary finding into a follow-up and to keep the policy working. [owner_choices.py](/src/forge/owner_choices.py:17) applies that policy to open functional findings, which no longer hold once converted. The plan does not say which rule wins.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - the plan says the `auto_more_round` policy now covers only an open functional P0 or required finding at the limit; ordinary ones are follow-ups first.

9. Advisory: Functional: the proposed dismissal match can hide a different defect on the same line.  
   Raise: Functional  
   Case: normal use - a reviewer dismisses one claim about a line, then another reviewer reports a different problem at that line. For example, [roles.py](/src/forge/roles.py:83) both chooses the fallback and can select the builder’s family. The proposed same-area and same-line match treats distinct claims as the same defect, although the later problem is new evidence.  
   Gain 4, Work 3, Harm 3
   Disposition: keep - a different claim on the same line needs the same area and a same-text cited line; a different problem normally cites other evidence and reopens, and the cost of a rare miss is one repeated finding.

10. Blocking: Not done: moving an unchanged cited line reopens a reworded dismissal.  
    Raise: Not done  
    Case: normal use - a repair inserts lines above the cited code. The new review cites the same unchanged code at its new line number, but [the plan](/plans/FORGE-THINREVIEW-1.md:69) requires its `path:line` to appear among the old citations. The existing change check in [review.py](/src/forge/review.py:720) already treats a shifted line as unchanged.  
    Gain 3, Work 2, Harm 3
   Disposition: cut - the match now compares the text of the cited line at the dismissal's commit, not its number, and a test inserts lines above the cited code.

11. Advisory: Functional: the session that starts a read may not be the plan’s author.  
    Raise: Functional  
    Case: normal use - Claude writes a plan, then a Codex coordinator takes over and starts its read. [repo.py](/src/forge/repo.py:851) identifies the current session, so the proposed rule calls Codex the author and can select Claude to read Claude’s own plan.  
    Gain 4, Work 3, Harm 3
   Disposition: keep - the plan lists this as an accepted limit: a coordinator who takes over and starts the first read counts as the author; Forge cannot see who wrote the text.

12. Blocking: Not done: a two-tool repo can still use the author’s family for a read.  
    Raise: Not done  
    Case: normal use - `tools = both`, but the other tool is not installed. The plan retains the existing read-family rule, which [roles.py](/src/forge/roles.py:107) falls back to the current session when the other tool is missing. The stated single-tool exception covers `tools = claude` or `tools = codex`, not this configuration.  
    Gain 3, Work 2, Harm 3
   Disposition: cut - `read_family` now refuses with the install line when the other tool is missing in a `both` repo, and a test covers it.

13. Advisory: Test: the planned light-review check cannot have the requested input.  
    Raise: Test  
    Case: normal use - the RECORD task implements its listed review-prompt test. [review.py](/src/forge/review.py:853) selects the prototype light prompt only for fixes, while the plan says fixes have no read-note checks and that light review shows `none`; its test also requires that prompt to show the check.  
    Gain 3, Work 1, Harm 1
   Disposition: cut - the test now expects the light prompt of a fix to show the section as `none`, and the check in the task review prompt.

Not checked: `forge next`; the write-protection sandbox could not start.

## Round 2

14. Blocking: Not fixed 2: CI cannot find the first part’s plan checks.  
    Raise: Not done  
    Case: normal use - the first part closes with `--no-review` in a CI-test repo. The proposed `owed(top, item)` reads a local story branch or the checkout, but [forge-pr-check](/src/forge/prcheck.py:1) uses a base-branch checkout, where the unmerged notes are absent. The test job sees the notes, but [proof.check](/src/forge/proof.py:203) checks for missing entries only before a run. Both checks can pass without the note’s proof line.  
    Gain 5, Work 3, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

15. Blocking: Not fixed 2: after-merge checks are also required before merge.  
    Raise: Not done  
    Case: normal use - a note names a check that can run only after merge. The amended plan requires a proof line for every owed entry, including this one, while also saying it must remain nonblocking. [proof.check](/src/forge/proof.py:200) refuses a covered entry without a proof line, so the proposed pending finding alone cannot let the part close.  
    Gain 4, Work 2, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

16. Blocking: Not fixed 1: a named JavaScript test need not run or pass.  
    Raise: Not done  
    Case: normal use - a must-prove note names a skipped Vitest or Playwright test. [proof.check](/src/forge/proof.py:211) checks that the file exists but collects run results only for Python tests. The proposed reuse of that check can therefore accept the named test without proving it ran.  
    Gain 5, Work 3, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

17. Blocking: Not fixed 2: generated-file changes bypass the new proof gate.  
    Raise: Not done  
    Case: normal use - a part changes only files produced by `forge sync`, has a must-prove note, and is closed with `--no-review`. [proof.check](/src/forge/proof.py:193) returns before reading covered entries for Forge-generated-only changes. The new note line is therefore not required on this path.  
    Gain 3, Work 2, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

18. Blocking: Not fixed 3: independent leaf parts can all decline the same check.  
    Raise: Not done  
    Case: normal use - independent API and frontend parts run in parallel, and a read-limit note asks for a flow using both. Neither leaf has the other’s work, so both can give the newly allowed “not reachable in this part” answer. The plan assigns the check only to leaves and names no later part that must run it; the flow can merge without anyone proving it.  
    Gain 4, Work 2, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

19. Blocking: Not fixed 6: an existing high-harm read stop can be accepted without its waiting owner.  
    Raise: Not done  
    Case: normal use - a read stopped before upgrade still has an open high-harm note. [The amended detail](/plans/FORGE-THINREVIEW-1.md:71) gives it the automatic limit step on the next read, while the owner-facing promise says every pre-upgrade stop still waits for an answer. This also affects a stop for a serious unresolved problem, not just the lower-harm case in the first finding.  
    Gain 4, Work 2, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

20. Blocking: Not fixed 7: splitting a note assigned to one part leaves the proof with that part.  
    Raise: Not done  
    Case: normal use - the owner splits an unmet `must prove A` check. [task.py](/src/forge/task.py:136) creates a follow-up task, but the proposed `owed` rule still assigns the read note to A. A’s next brief and proof gate still require it, so changing only finding classification does not release an unproved check.  
    Gain 4, Work 2, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

21. Blocking: Not fixed 8: the saved extra-round permission is extended to P0s.  
    Raise: Not done  
    Case: normal use - a repo already has `auto_more_round = true` and the same functional P0 remains after two reviews. The amended plan grants another round automatically, although its owner-facing text says an open P0 stops for the owner. The existing [guide](/src/forge/templates/skill.md:2279) explicitly says P0s do not use that standing permission.  
    Gain 4, Work 2, Harm 3
   Disposition: keep - Owner accepted; notes 14-21 become must-fix lines in the covered Done-when details

22. Advisory: Disputed keep 9: identical text on a different line can carry a dismissal.  
    Raise: Functional  
    Case: normal use - two JavaScript functions in one file contain the same `return false;` line. The amended match compares line text and area; [review.area](/src/forge/review.py:197) uses the whole file as the area for JavaScript. A new finding on the second line can therefore inherit a dismissal of the first, even though it cites different code.  
    Gain 4, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

23. Advisory: Functional: a split required finding can disappear from the pull request.  
    Raise: Functional  
    Case: normal use - the owner splits a required finding. The amendment makes it nonblocking without clearing `required_done_when`, but [pr_block.py](/src/forge/pr_block.py:40) still puts that finding in the blocking list, which it does not print for a clean review. [score.remember](/src/forge/score.py:189) also keeps it as open rather than a follow-up.  
    Gain 3, Work 2, Harm 2
   Disposition: keep - below the bar (follow-up)

24. Advisory: Unproven: the repeated-note rule may miss the required label.  
    Raise: Test  
    Case: normal use - the reader returns `Blocking: Not fixed 3: ...`. The plan names a title starting `Not fixed 3:`, while [cold-read.md](/src/forge/templates/cold-read.md:301) requires the `Blocking:` prefix. The proposed test can use the unprefixed form, as existing [read-loop tests](/tests/test_readloop_rounds.py:350) do, and pass while the actual labelled note is missed.  
    Gain 3, Work 3, Harm 3

Not checked: `forge next`; the write-protection sandbox could not start. The story-state edit was already present when this read began and stayed unchanged.
   Disposition: keep - below the bar (follow-up)
