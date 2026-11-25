---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-25T06:31:31.043746+00:00
seconds: 324.662
read_hash: e74014b544c867ecef3d5bf4de9a33c74680b528
round: 2
passed: no
doc_seen: 60d68af23d585cdb28a7bc4930f278caed7aae08
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: ab551a32e5be60581a7c9cfcab6a02390d9f11f4
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a2115a-1dc6-7df3-b9d6-4d1c5ee13d88
session:
loop_choice: accept
loop_reason: Owner accepted on 25 Nov 2026 with three fixes: rare rule only below Harm 4, later notes stay in the read notes, review treats limit checks as required
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

1. Blocking: Not done: Required checks do not reach the workers assigned to perform them.  
   Raise: Not done  
   Case: normal use - A read reaches its limit with an open note about one task. The plan puts the check in a new builder subsection, but [worker.py](/src/forge/worker.py:610) sends workers only their covered Done-when details and the plan’s Notes, with no assignment for the new subsection. The planned test checks the plan and approval state, not the worker’s brief.  
   Gain 5, Work 3, Harm 3
   Disposition: cut (checks go to the plan's Notes, which every story worker receives)

2. Blocking: Not done: A read that reaches the limit still asks the owner when the round finishes.  
   Raise: Not done  
   Case: normal use - A blocking note remains at the end of round two. The plan changes the stop at the start of [story.read](/src/forge/story.py:197), but [read_result](/src/forge/story.py:431) independently raises the owner question as soon as that round ends.  
   Gain 4, Work 2, Harm 3
   Disposition: cut (detail 3 changes read_result too)

3. Blocking: Not done: An existing stopped read can lose its owner choice after upgrade.  
   Raise: Not done  
   Case: normal use - Before upgrade, round two stopped on a Gain 4, Harm 2 note. Applying the new later-round rule makes [passed](/src/forge/story.py:723) return true, so [stopped](/src/forge/story.py:738) becomes false and `--resolve` is refused. The plan explicitly promises that this existing stop will still wait for the owner.  
   Gain 4, Work 2, Harm 3
   Disposition: cut (--resolve stays accepted for any record at the limit with no choice)

4. Blocking: Not done: An earlier note can remain unfixed without being recognized.  
   Raise: Not done  
   Case: normal use - A reader finds that a previous `cut` did not fix the problem and reports it as “Blocking: the earlier note is still open.” The planned rule recognizes only titles starting with `Not fixed` or `Disputed keep`, while the current [reader instructions](/src/forge/templates/cold-read.md:285) do not require `Not fixed` and also tell the reader not to repeat a disposed note. They require `Blocking:` before the title.  
   Gain 4, Work 2, Harm 3
   Disposition: cut (cold-read.md requires the Not fixed <n>: prefix)

5. Blocking: Not done: An unfixed-note report can be marked kept before the new round rule sees it.  
   Raise: Not done  
   Case: normal use - A round-two `Not fixed` note has Gain 3, Work 1, Harm 2. [score.notes](/src/forge/score.py:69) automatically gives it a below-bar keep disposition before [read_result](/src/forge/story.py:393) checks the round. The limit handler can then omit it from open required checks even though the new rule says it holds.  
   Gain 3, Work 2, Harm 3
   Disposition: cut (score.notes never auto-keeps Not fixed or Disputed keep notes)

6. Blocking: Not done: A new serious note can miss its promised extra round.  
   Raise: Not done  
   Case: normal use - Round one finds a serious problem that is fixed; round two finds a different note with Harm 4. The [existing stop rule](/src/forge/story.py:738), which the plan says to keep, checks whether *any* serious note appeared in the previous round. It stops without giving the new note its own extra round.  
   Gain 3, Work 2, Harm 3
   Disposition: cut (the promise now matches today's P0 rule)

7. Blocking: Plan gap: The round-limit action has no destination for specs or decisions.  
   Raise: Plan gap  
   Case: normal use - A spec or decision reaches its read limit with an open note. The same [read command](/src/forge/story.py:933) handles those documents, but the plan only defines writing checks into a story plan’s builder section; a spec or decision need not have that section or a task to receive the checks.  
   Gain 4, Work 2, Harm 3
   Disposition: cut (checks go to the document's Notes for specs and decisions too)

8. Blocking: Gate: The behavior changes and their guidance are assigned to separate changes.  
   Raise: Gate  
   Case: normal use - BAR changes which notes a coordinator must answer, and LIMIT changes the limit step, while GUIDE owns the guidance and waits for LIMIT. The [review rule](/AGENTS.md:135) requires the guide or worker brief update in the same change.  
   Gain 4, Work 2, Harm 2
   Disposition: cut (two tasks, each with its own guide text)

9. Blocking: Not done: The rendered worker brief still gives the old limit instructions.  
   Raise: Not done  
   Case: normal use - A worker receives its brief after the change. [worker.py](/src/forge/worker.py:27) injects text saying that a cold read stops for the owner’s choice. Updating the brief template alone does not change that injected text.  
   Gain 3, Work 2, Harm 3
   Disposition: cut (LIMIT covers worker.py's injected wording)

10. Blocking: Not done: The planned rare-frequency check does not match the required note format.  
    Raise: Not done  
    Case: normal use - A reader writes `Adds work: protect branch ownership; F 1 x H 3 ...`, as the [read template](/src/forge/templates/cold-read.md:122) requires. The [plan](/plans/FORGE-READCHURN-1.md:41) recognizes only an `Adds work:` line that starts with `F 1`, so this valid note will not receive the promised treatment.  
    Gain 3, Work 1, Harm 3
   Disposition: cut (F 1 x anywhere on the Adds work line)

## Round 2

11. Blocking: A frequency score can make a normal-use data-loss note pass.  
    Raise: Data loss  
    Case: normal use - A repository already has a branch that a planned force-push and cleanup would overwrite and delete. The earlier [branch-ownership note](/plans/FORGE-TRAIN-1.read.md:36) describes that case as normal use, scores it Harm 4, and includes `F 1 x`. The amended [plan](/plans/FORGE-READCHURN-1.md:41) now treats that line as rare regardless of its case or Harm, so the note would no longer hold the read.  
    Gain 5, Work 2, Harm 4
    Disposition: cut (the rare rule applies only below Harm 4)

12. Advisory: Later notes that do not hold still do not reach builders.  
    Raise: Not done  
    Case: normal use - Round two contains only a new advisory note. The read passes, so the limit handler does not copy it into Notes; advisory notes are also forbidden from the plan. [worker.py](/src/forge/worker.py:610) does not send the separate read-notes file to the worker.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

13. Advisory: The new required checks are treated as accepted notes during review.  
    Raise: Not done  
    Case: normal use - A builder omits a test required only by a check added at the read limit. The amended plan marks that note kept, so [review.py](/src/forge/review.py:630) presents it as accepted; the [review instructions](/src/forge/templates/review.md:266) say Notes cannot block as `Not done`. The planned limit test does not check that the builder performs the check.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)
