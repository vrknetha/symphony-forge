---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-27T10:46:41.472448+00:00
seconds: 702.367
read_hash: 7971c2fb0c145888e477ab3e5def1c339f1b62b6
round: 2
passed: yes
doc_seen: 7971c2fb0c145888e477ab3e5def1c339f1b62b6
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: a5e403983b2a061f58e1e85a3f70eeefca123f0a
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21c89-8770-7031-923e-25a864266a51
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

1. Blocking: Not done: item 1 — fixed pytest splits can skip changed tests.  
   Raise: Not done  
   Case: normal use - A repo enables `small` with `--splits 4 --group {group}` in its test command.  
   The plan forces one group, but [prcheck.py](/src/forge/prcheck.py:412) does not recognize that fixed split count, and [repo.py](/src/forge/repo.py:663) leaves it at four. Only group 1 runs, so changed tests in the other groups can be missed.  
   Gain 4, Work 3, Harm 3
   Disposition: keep accepted limit: a hand-written fixed `--splits N` command is the same case as today's docs-only one-group path; the guide already says to use `{groups}`, and the plan's accepted limits now say it

2. Blocking: Not done: item 1 — a custom pytest command bypasses the small selector.  
   Raise: Not done  
   Case: normal use - A pytest repo has `fast_test = "pytest -q"` and enables `small`.  
   [review.py](/src/forge/review.py:374) runs `fast_test` directly. The plan changes only the picker in `pytest_tests`, so close and the pull request check still run the custom command instead of the promised small set.  
   Gain 4, Work 3, Harm 3
   Disposition: keep accepted limit: a custom `fast_test` command is the repo's own choice and runs as before; making `small` rewrite it would add code for a rare case. The guide and the accepted limits now say `small` changes only Forge's picker

3. Blocking: Not done: item 2 — a repo’s own full-suite workflow may have no nightly run.  
   Raise: Not done  
   Case: normal use - A CI repo enables `small` while using `full_suite_workflow` for a manual full run.  
   [prcheck.py](/src/forge/prcheck.py:306) omits Forge’s scheduled job when that setting is present, and the [guide](/src/forge/templates/skill.md:2425) requires the repo’s workflow to support manual runs but does not require a schedule. The promised nightly backstop can therefore be absent.  
   Gain 4, Work 3, Harm 3
   Disposition: keep accepted limit: a repo with its own `full_suite_workflow` is a rare custom setup; the guide now tells the agent to set `small` only when a nightly full run exists, and the accepted limits say so

4. Blocking: Plan gap — expanding the basic-tests list breaks a test outside the task’s scope.  
   Raise: Plan gap  
   Case: normal use - The builder adds the requested tests and runs the existing suite.  
   [test_required_repo_rules.py](/tests/test_required_repo_rules.py:38) copies the real list but creates fixtures for only its six current entries. The new entries will name missing tests, and this file is absent from the task’s Tests cell.  
   Gain 4, Work 2, Harm 3
   Disposition: cut item 1 details now change `tests/test_required_repo_rules.py` to read its entries from `.forge/always-tests.txt`; the file is added to the task's Tests cell

5. Blocking: Not done: item 2 — `forge next` does not show the failed run’s link.  
   Raise: Not done  
   Case: normal use - A nightly full run fails and the agent checks `forge next`.  
   [nextstep.py](/src/forge/nextstep.py:430) prints the failure, test names and fix command, but omits the run URL. The plan says this already works and excludes that file from the task.  
   Gain 3, Work 2, Harm 2
   Disposition: cut the claim now says the board links the failed run and `forge next` names the failed jobs and the fix command; Done-when 2 and the fourth bullet of What changes were reworded the same way

6. Blocking: Plan gap — the worker guide would promise the same test set for two different runs.  
   Raise: Plan gap  
   Case: normal use - A task’s Proof list names an existing test outside its Tests column.  
   The plan directs the brief to say bare `forge test` and close run the same set. But [review.py](/src/forge/review.py:492) marks bare runs as worker runs, and [fasttest.py](/src/forge/fasttest.py:852) selects the task’s Tests column for those runs. The planned non-worker path instead reads the Proof list.  
   Gain 3, Work 2, Harm 3
   Disposition: cut the brief sentence now says bare `forge test` (a worker run) runs the Tests column, touched test files and basic tests, and that close and the pull request check also run the Proof list tests

7. Blocking: Plan gap — merging the repair does not by itself clear the merge hold.  
   Raise: Plan gap  
   Case: normal use - A nightly run fails and its repair merges before the next full run.  
   The plan says other tasks wait until the fix merges. [merge.py](/src/forge/merge.py:430) instead keeps the hold until a later full run passes; its refusal explicitly calls for that run after the repair.  
   Gain 3, Work 1, Harm 3
   Disposition: cut the plan now says other tasks wait until a later full run passes after the fix (nightly or by hand); the accepted limits and the `merge.red` description say the same

Skipped `forge next` because it can remove finished worktrees; this read had to leave files unchanged.

## Round 2

8. Advisory: Not done: item 1 — basic tests can fail in a nested Python project.  
   Raise: Not done  
   Case: normal use - A repo uses `cd backend && pytest tests` and lists `backend/tests/test_smoke.py` as a basic test.  
   [fasttest.py](/src/forge/fasttest.py:138) appends the repository-relative path unchanged. Pytest receives it after `cd backend` and looks under `backend/backend/tests`, so the run fails. The planned test uses repository-root tests and would not catch this.  
   Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

9. Advisory: Plan gap — the revised worker brief says touched test files run, but a task can skip them.  
   Raise: Plan gap  
   Case: normal use - A task’s Tests column names one test in a file, and the worker also updates another test in that file.  
   The [plan](/plans/FORGE-PRSMOKE-1.md:54) now says bare `forge test` runs touched test files. The retained task path in [fasttest.py](/src/forge/fasttest.py:852) clears the changed-file selection and runs only the named test, so the other updated test is skipped.  
   Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

10. Advisory: Not done: item 1 — mixed Python and JavaScript repos can run extra tests.  
    Raise: Not done  
    Case: normal use - A repo uses `pytest ... && vitest run`, and a pull request changes a JavaScript module.  
    The planned change narrows pytest, but [fasttest.py](/src/forge/fasttest.py:322) still runs Vitest with `--changed`. It can select unchanged JavaScript tests outside the Proof list and basic list, contrary to the promised test set.  
    Gain 3, Work 3, Harm 2

Skipped `forge next` because it can remove finished worktrees.
   Disposition: keep - below the bar (follow-up)
