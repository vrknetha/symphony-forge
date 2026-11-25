---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-25T07:15:24.763293+00:00
seconds: 274.05
read_hash: 8cb9eba20c052e718e6e9008f754eb04a2241173
round: 2
passed: no
doc_seen: 8cb9eba20c052e718e6e9008f754eb04a2241173
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 93b4b4869381de0f32ac4c70b12783b681e10ce4
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a2117f-64b5-7630-acfb-35ea9c984321
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

1. Blocking: Not done: item 2 can delete an uncommitted lockfile.
   
   Raise: Data loss  
   Case: normal use - A merged folder has a modified or staged `uv.lock`. [task.py](/src/forge/task.py:953) excludes that change from `worktree_files`, and [doctor.py](/src/forge/doctor.py:443) removes the folder with `--force`. The plan explicitly reuses both behaviors despite promising to keep every uncommitted file.  
   Gain 5, Work 3, Harm 5
   Disposition: cut

2. Blocking: A reopened pull request can lose its checkout while the cached result is fresh.
   
   Raise: Functional  
   Case: normal use - Someone reopens a closed pull request within a minute without changing its branch. The planned cache can still report it closed; the remote-head check also succeeds, so cleanup can remove its folder. The 60-second cache behavior is shown in [board_facts.py](/src/forge/board_facts.py:88), while [the plan](/plans/FORGE-TIDYUP-1.md:34) requires there to be no open pull request.  
   Gain 4, Work 2, Harm 2
   Disposition: cut

3. Blocking: Cleanup can run in an existing repo before that repo upgrades.
   
   Raise: Functional  
   Case: normal use - A developer installs a newer Forge for one repo, then runs `forge next` in another repo pinned to an older release. `next` is declared as not changing state in [nextstep.py](/src/forge/nextstep.py:27), so [cli.py](/src/forge/cli.py:150) does not select the pinned release before running the new cleanup. This conflicts with the plan’s upgrade delivery.  
   Gain 4, Work 2, Harm 3
   Disposition: cut

4. Blocking: Not done: item 4 misses closed work after cleanup removes its local folder.
   
   Raise: Not done  
   Case: normal use - `forge next` removes a clean folder for a closed pull request whose branch remains on GitHub. A later `forge land` sweep only scans existing local worktrees in [land.py](/src/forge/land.py:486), so it leaves that unmerged item out. The planned queue change only changes the status filter.  
   Gain 4, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

5. Blocking: Not done: item 4 does not resume a builder that stopped after a partial commit.
   
   Raise: Not done  
   Case: normal use - A builder commits part of a fix and stops before finishing. The proposed sweep sends it to the single-item path, but [land.py](/src/forge/land.py:99) starts a builder only for the listed unbuilt cases; [task.py](/src/forge/task.py:880) treats a work commit as built. Land proceeds to close without resuming that builder.  
   Gain 4, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

6. Blocking: The proposed drop step cannot drop one story part.
   
   Raise: Plan gap  
   Case: normal use - An owner wants to drop one stalled part of a story. [The plan](/plans/FORGE-TIDYUP-1.md:39) proposes `forge story drop`, but [intake.py](/src/forge/intake.py:201) accepts a story key, drops the whole plan, and refuses when a part has already merged.  
   Gain 4, Work 2, Harm 3
   Disposition: cut

7. Blocking: Not done: item 1 leaves a clean local branch that is behind its merged pull request.
   
   Raise: Not done  
   Case: normal use - A teammate adds commits to the same branch on another machine and merges its pull request. The local branch has no commits outside that request, but [the planned equality check](/plans/FORGE-TIDYUP-1.md:34), matching [doctor.py](/src/forge/doctor.py:80), keeps it because the heads differ.  
   Gain 4, Work 3, Harm 2
   Disposition: keep - below the bar (follow-up)

8. Blocking: The first task cannot ship its declared cleanup within its scope.
   
   Raise: Plan gap  
   Case: normal use - TIDY must wire cleanup into `forge land`, but its scope excludes [land.py](/src/forge/land.py:45), which belongs to the later SWEEP task. The shared cleanup function is also unnamed, and the guide update is assigned to SWEEP even though [the review rule](/AGENTS.md:135) requires the relevant guide update in the same change. The planned cleanup test exercises only `forge next`.  
   Gain 4, Work 1, Harm 2
   Disposition: cut

9. Blocking: The task test lists omit existing tests that the planned changes invalidate.
   
   Raise: Test  
   Case: normal use - [test_doctor_fix.py](/tests/test_doctor_fix.py:251) stubs and asserts the per-branch GitHub request that TIDY replaces. [test_queue_land_all.py](/tests/test_queue_land_all.py:304) expects bare `forge land` to refuse and unfinished builders to be left out. Neither task names these tests for amendment.  
   Gain 4, Work 2, Harm 2
   Disposition: cut

10. Blocking: Not done: item 1 promises a count even when no folder is removed.
    
    Raise: Not done  
    Case: normal use - GitHub responds and there are no finished folders. [The approved-result text](/plans/FORGE-TIDYUP-1.md:21) promises a count, while the builder details print one only when the count is greater than zero. [nextstep.py](/src/forge/nextstep.py:183) owns the current command output.  
    Gain 3, Work 1, Harm 1
   Disposition: cut

11. Blocking: Not done: item 1 promises cleanup of the folder running the command.
    
    Raise: Not done  
    Case: normal use - A person merges a pull request on GitHub while a shell is in its clean worktree, then runs `forge next` there. The public result says every qualifying merged folder is removed, but [the builder details](/plans/FORGE-TIDYUP-1.md:36) deliberately keep the current folder, as [doctor.py](/src/forge/doctor.py:75) does today.  
    Gain 3, Work 1, Harm 2
   Disposition: cut

12. Advisory: Unproven: item 4 can repeat owner decisions before its final list.
    
    Raise: Test  
    Case: normal use - Two items stop for owner decisions. [land.py](/src/forge/land.py:965) relays each child’s output during the run and then prints the collected decisions. The planned test has two successful items, so it can pass without proving decisions appear only once.  
    Gain 3, Work 2, Harm 2

I did not run `forge next`: automatic approval review rejected the sandboxed command because it required approval.
   Disposition: keep - below the bar (follow-up)

## Round 2

13. Blocking: Finding 1 is not closed: the test-only exception also deletes hand-edited lockfiles.
    
    Raise: Data loss  
    Case: normal use - A merged folder contains a manually edited or staged `uv.lock`. [The amended plan](/plans/FORGE-TIDYUP-1.md:8) promises to keep changes that tests did not make, but the retained [worktree_files check](/src/forge/task.py:962) excludes every tracked `uv.lock` change regardless of its source. [Doctor’s removal](/src/forge/doctor.py:443) then deletes it with the folder.  
    Gain 5, Work 3, Harm 5

14. Advisory: A land sweep can repeat the uncached GitHub scan for every queued item.
    
    Raise: Scale  
    Case: normal use - A sweep has ten queued changes. [The amended plan](/plans/FORGE-TIDYUP-1.md:34) calls cleanup from `forge land` without a cache, and [the queue](/src/forge/land.py:951) starts a separate `forge land` process for each item. That can make at least eleven full pull-request listings for one sweep.  
    Adds work: avoid redundant scans in queued child processes; F 1 x H 2 = 2; 2 x C = 2.  
    Gain 3, Work 2, Harm 2

I did not run `forge next`. The story’s bookkeeping file was already modified when this read began and remained unchanged during it.
   Disposition: keep - below the bar (follow-up)
