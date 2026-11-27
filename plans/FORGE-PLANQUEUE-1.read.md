---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-27T05:55:21.676666+00:00
seconds: 613.685
read_hash: 28f5de422690719804054b662637dc31c9147050
round: 2
passed: no
doc_seen: 28f5de422690719804054b662637dc31c9147050
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 9c0cb49434536985aea8a3c26493704cdf23d015
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21b7b-ed92-75b1-8fff-6675548f2f3a
session:
loop_choice: accept
loop_reason: Owner accepted; builder fixes both in its first note: commit the story record together with the owner's answer, and an answered question always gets one more write turn before the cold read
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

1. Blocking: Restart recovery can erase a person’s plan edits.
   
   Raise: Data loss — [the plan](/plans/FORGE-PLANQUEUE-1.md:52) says a free lock with a turn marker causes both plan files to be restored from the last commit. The marker does not distinguish the interrupted turn’s changes from edits a person made afterward.
   
   Case: normal use - a planning turn stops, the owner edits the plan, and the next Forge command restarts the runner.
   
   Gain 5, Work 3, Harm 4
   Disposition: cut the marker restore is gone; a killed turn is run again on the files as they are, so nothing is overwritten and a person's later edit is kept (Locks and restart; the restart test now checks the kept line)

2. Blocking: Not done: item 1: a read with findings leaves changes that stop the answer step.
   
   Raise: Not done — [the plan](/plans/FORGE-PLANQUEUE-1.md:46) uses a new child for each step and leaves a folder alone when it contains changes that child did not make. A [read with findings](/src/forge/story.py:425) leaves both the notes and story state uncommitted; the following answer child did not make them. The plan gives it no way to distinguish those changes from a person’s edits.
   
   Case: normal use - the first cold read returns a blocking note.
   
   Gain 5, Work 3, Harm 3
   Disposition: cut the read child now commits the notes file and the story's record after `forge read` exits, so the answer child finds a clean folder (Read step)

3. Blocking: Not done: item 4: an edited plan can make the runner retry without pause.
   
   Raise: Scale — [the plan](/plans/FORGE-PLANQUEUE-1.md:52) says a child exits zero when it finds someone’s uncommitted edit, while the next line says zero starts another pass at once. The same unchanged edit causes another child to exit zero, repeatedly.
   
   Case: normal use - a person saves an uncommitted plan edit while the runner is active.
   
   Gain 4, Work 2, Harm 3
   Disposition: cut a folder left alone now exits with code 3, the runner parks it in the quiet set until the next wake, and the test checks no child starts again (Runner side, Locks and restart)

4. Blocking: Not done: item 1: the writer cannot finish the top of some new plans.
   
   Raise: Plan gap — [the write step](/plans/FORGE-PLANQUEUE-1.md:49) forbids changes above `## Risks`, but [the story template](/src/forge/templates/story.md:5) puts placeholders and comments there. The specified `forge story new` test therefore cannot both keep that rule and remove the placeholders. Also, a small screen change started through [intake](/src/forge/intake.py:212) needs a `Design: none` line in that section before [the design check](/src/forge/design.py:127) will pass.
   
   Case: normal use - a new story starts from the template, or makes a small change to an existing screen.
   
   Gain 4, Work 2, Harm 3
   Disposition: cut the writer may now fix the owner's top sections for plain wording, fill the parts line, remove template text and add the `Design: none (<why>)` line; only their meaning stays fixed (Write step)

5. Blocking: Not done: item 1: amending a note does not satisfy the next read.
   
   Raise: Plan gap — [the answer prompt](/plans/FORGE-PLANQUEUE-1.md:51) tells the writer to amend the plan **or** add a disposition. [Forge’s read gate](/src/forge/story.py:227) requires a disposition for every blocking note even when the plan was amended.
   
   Case: normal use - the writer fixes a blocking note by changing the plan.
   
   Gain 4, Work 1, Harm 3
   Disposition: cut the answer prompt now requires a disposition under every blocking note, with or without a plan change, as the read gate demands (Answer step)

6. Blocking: Not done: items 1 and 3: a task row can make an unfinished draft skip the writer.
   
   Raise: Plan gap — [the step rule](/plans/FORGE-PLANQUEUE-1.md:48) calls a plan a draft only when its Tasks table has no row. [A story promoted from a fix](/src/forge/story.py:121) starts with a row but still has template text. The same rule can skip the remaining writing after a writer asks a question having already added a row.
   
   Case: normal use - a fix becomes a story, or the owner answers a question in a partly written plan.
   
   Gain 4, Work 2, Harm 3
   Disposition: cut a draft is now any plan that still holds template text (a `<!--` comment or the Evidence placeholder line), not an empty Tasks table; tests cover a plan promoted from a fix (Which step)

7. Blocking: Not done: item 1: an added idea can leave an approved story waiting without a notice.
   
   Raise: Functional — [intake](/src/forge/intake.py:193) can add an idea to an existing story and change its approval text. [Approval](/src/forge/approval.py:100) then treats the old approval as stale, but [the plan’s selection rule](/plans/FORGE-PLANQUEUE-1.md:47) skips every story that has an approval hash.
   
   Case: normal use - the owner starts another idea that Forge adds to an already approved story.
   
   Gain 4, Work 2, Harm 3
   Disposition: cut stories are now chosen with `approval.waiting_digest`, the call `forge next` uses, so a story with a stale approval is planned again (Which stories)

8. Blocking: Not done: item 1: the existing reader rule can select the writer’s tool.
   
   Raise: Plan gap — [the plan](/plans/FORGE-PLANQUEUE-1.md:50) says passing the worker family to `forge read` makes the other tool read. [Reader selection](/src/forge/roles.py:101) instead honors a configured reviewer or an installed reader from an earlier round, even when that is the writer’s family.
   
   Case: normal use - both tools are installed, and the configured reviewer or earlier reader is also the plan writer.
   
   - Open question: When the configured reader is also the writer, should Forge use the other tool or keep the configured reader?
     Touches: cold-read tool selection
     Why we ask: The plan promises both an independent tool and the existing selection rule.
     Default: Keep the existing selection and state the exception.
     Why this default: It preserves the repo’s configured reader.
     If the default stands: The writer’s tool can read its own plan.
     Due: 2026-12-04
   
   Gain 4, Work 2, Harm 3
   Disposition: cut the default stands: the configured reader keeps reading even when it wrote the plan; the exception is now stated under Accepted limits

9. Blocking: Split: PLAN → restart-safe planning steps and runner integration.
   
   Raise: Plan gap — [the single task](/plans/FORGE-PLANQUEUE-1.md:69) covers all four Done-when items, while [the cold-read rule](/src/forge/templates/cold-read.md:177) requires a split above three. The proposed writer prompt also directs future plans toward one part without that limit.
   
   Case: normal use - a story has four outcomes to deliver.
   
   Gain 4, Work 2, Harm 2
   Disposition: cut the three Done-when items now match one task (the restart item is joined to item 1), and the write prompt applies the cold read's own split rule instead of one part per story (Done when, Write step)

## Round 2

10. Blocking: Not done: item 3: answering a stop can leave the story parked.
   
   Raise: Not done — When a question is answered in the story checkout, [the approval hook](/src/forge/approval.py:328) updates the story record without committing it. [Resolving the read](/src/forge/story.py:199) commits the plan and notes, but not that record. The new [dirty-folder rule](/plans/FORGE-PLANQUEUE-1.md:52) then silently leaves the story alone. The planned test runs the resolve command without exercising the question hook.
   
   Case: normal use - the owner answers a round-limit question through the chat’s question tool.
   
   Gain 5, Work 3, Harm 3
   Disposition: keep - Owner accepted; builder fixes both in its first note: commit the story record together with the owner's answer, and an answered question always gets one more write turn before the cold read

11. Blocking: Not done: item 3: an owner’s answer can bypass the writer.
   
   Raise: Not done — [The amended prompt](/plans/FORGE-PLANQUEUE-1.md:49) can leave a complete plan with no template comments and a question in Notes. After the owner records an answer there, [the new draft test](/plans/FORGE-PLANQUEUE-1.md:48) does not select another write turn; Forge proceeds to the cold read. The answer can therefore remain in Notes without changing the behavior or tasks the owner chose.
   
   Case: normal use - the writer completes a draft, asks the owner to choose between two behaviors, and the owner answers.
   
   Gain 5, Work 3, Harm 3
   Disposition: keep - Owner accepted; builder fixes both in its first note: commit the story record together with the owner's answer, and an answered question always gets one more write turn before the cold read

12. Advisory: An added idea can reach approval without being planned into tasks.
   
   Raise: Functional — [Intake](/src/forge/intake.py:193) adds the new result to the top of an existing plan. If that plan has no template comments, [the amended step rule](/plans/FORGE-PLANQUEUE-1.md:48) chooses the read rather than the writer. [The parser](/src/forge/story.py:504) does not require every result to have a task, so a passing reader can leave the new result unbuilt.
   
   Case: normal use - Forge adds an idea to a previously approved, completed plan.
   
   Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

13. Advisory: Antigravity does not fall back to Claude when Codex is unavailable.
   
   Raise: Functional — [The plan](/plans/FORGE-PLANQUEUE-1.md:50) says the new Antigravity path tries Codex, then Claude. With no saved or configured reader, [the existing selector](/src/forge/roles.py:101) instead falls back to the reported coordinator, which the plan sets to Antigravity.
   
   Case: normal use - Antigravity writes a fresh plan, Claude is installed, and the Codex SDK is unavailable.
   
   Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

14. Advisory: A discarded read can commit a person’s unfinished notes.
   
   Raise: Functional — [The read step](/plans/FORGE-PLANQUEUE-1.md:50) commits the notes and story record after every exit. [A cold read discards its result](/src/forge/story.py:378) if a file changes during the read, but the proposed commit still stages the whole notes file.
   
   Case: normal use - a person edits the read notes while a cold read is running.
   
   Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

15. Advisory: The dirty-folder rule overlooks other uncommitted files.
   
   Raise: Plan gap — [The accepted limit](/plans/FORGE-PLANQUEUE-1.md:35) says a plan folder with uncommitted changes is left alone, but [the implementation rule](/plans/FORGE-PLANQUEUE-1.md:52) checks only the plan, read notes, and story record.
   
   Case: normal use - a person has uncommitted design files in the story folder.
   
   Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)
