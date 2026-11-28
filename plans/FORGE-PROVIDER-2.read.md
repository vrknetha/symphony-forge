---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-28T02:39:24.483518+00:00
seconds: 790.015
read_hash: bd1d4bfe26e6949316b37ff172c473237a261d25
round: 1
passed: no
doc_seen: bd1d4bfe26e6949316b37ff172c473237a261d25
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21ff9-89ae-7901-913c-09e951d37fcb
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

1. Blocking: Test runs can read or alter another run on the same box.
   Raise: Security
   Case: normal use - two branches test at the same time.
   [The plan](/plans/FORGE-PROVIDER-2.md:82) gives the shared machine role read access to every run’s input and write access to every run’s output. Both commands also share the machine. A test can discover the other run’s ID, read its uncommitted files, or replace its result; the laptop then uses those results for its [proof check](/src/forge/review.py:543).
   Not done: item 2’s claimed restriction to the keys a run is given.
   Gain 5, Work 4, Harm 4
   Disposition: cut - each box run is its own user with its own private folder, and only the root box script calls S3, so run code cannot read or replace another run's files; IMDS is blocked for run users. The builder proves it in `test_2` (two runs at once) and `test_3` (role has no list right); the Docker-group exception is now in Risks.

2. Blocking: Removing an approved test file does not remove its value from the box’s reach.
   Raise: Security
   Case: normal use - an owner removes a file from `aws_test_files`.
   [The plan](/plans/FORGE-PROVIDER-2.md:75) leaves it in the current secret until `files` runs again. Even after that, the box role can retrieve the preceding secret version: [AWS retains it as `AWSPREVIOUS`](https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html).
   Not done: item 2 allows only currently approved files.
   Gain 4, Work 3, Harm 4
   Disposition: cut - the box writes only the names in `meta.json`, `files` removes the `AWSPREVIOUS` label after each write, and the box role reads only the `AWSCURRENT` stage. Proved in `test_2` and `test_3`.

3. Blocking: The upload rule does not safely handle Git submodules.
   Raise: Security
   Case: normal use - a repo has a submodule containing an ignored `.env` file.
   [The upload](/plans/FORGE-PROVIDER-2.md:74) takes paths from `git ls-files`; a submodule appears as a directory entry, not a list of its allowed files. Recursively archiving that entry can include its ignored files and `.git`; omitting its contents leaves the tested tree incomplete. Forge already recognizes [submodule checkouts](/tests/test_doctor_fix.py:338).
   Not done: item 2 excludes ignored files and Git history.
   Gain 4, Work 3, Harm 4
   Disposition: cut - a submodule (mode 160000) keeps the run on the laptop with one line; proved in `test_2`.

4. Blocking: The claim that no old secret leaves is false for a changed file.
   Raise: Data loss
   Case: normal use - a branch removes a previously committed credential from a file.
   [The upload rule](/plans/FORGE-PROVIDER-2.md:74) sends that file’s base version, including the removed credential. The [Notes](/plans/FORGE-PROVIDER-2.md:132) say no old secret leaves, while the risk text does not identify this exposure.
   Gain 3, Work 1, Harm 4
   Disposition: cut - the base versions come from the merge base on the default branch, so they are already published; the Notes and Risks now say so instead of claiming no old secret leaves.

5. Blocking: Turning boxes off can leave Actions tests waiting for deleted runners.
   Raise: Functional
   Case: normal use - a private repo uses both AWS Actions runners and test boxes.
   [The turn-off order](/plans/FORGE-PROVIDER-2.md:19) deletes their shared stack without first removing `test_runner = "forge-aws"`. The generated workflow continues to use that [test runner label](/src/forge/prcheck.py:310).
   Adds work: restore the existing runner-setting step; F 2 x H 2 = 4; 2 x C = 4.
   Gain 4, Work 2, Harm 3
   Disposition: cut - the turn-off bullet and the SHOW part now remove `test_runner = "forge-aws"` first and `off` refuses while the default branch still sets it; proved in `test_6`.

6. Blocking: Stop releases a box reservation even when the test may still be running.
   Raise: Not done
   Case: normal use - a person stops a run while AWS cannot confirm cancellation.
   [SHOW](/plans/FORGE-PROVIDER-2.md:102) explicitly releases the reservation and removes the row after two minutes without confirmation. A subsequent run can then occupy that capacity while the first continues, contrary to [item 6](/plans/FORGE-PROVIDER-2.md:37) and the confirmed-end rule.
   Gain 4, Work 2, Harm 3
   Disposition: cut - an unconfirmed stop sends no `release`, so the place stays held until the box ends; proved in `test_6`.

7. Blocking: An ordinary `forge test` does not receive the base needed for test selection.
   Raise: Not done
   Case: normal use - a builder runs `forge test` after editing a tracked Python test.
   [SHIP](/plans/FORGE-PROVIDER-2.md:74) includes base versions only for a change run, but the box must construct two commits for every run. Ordinary `forge test` also selects against a base in [review.close_test](/src/forge/review.py:374). With only the working tree, the box has no original contents from which to reconstruct that diff.
   Not done: items 2 and 5 require the allowed tree and the laptop run’s result.
   Gain 5, Work 3, Harm 3
   Disposition: cut - the comparison data is sent for every run, plain `forge test` included; proved in `test_2`.

8. Blocking: New untracked tests disappear from the box’s change selection.
   Raise: Functional
   Case: normal use - a builder creates an untracked Python test and runs `forge test`.
   [SHIP](/plans/FORGE-PROVIDER-2.md:74) includes the file in the working tree but obtains change names from `git diff`, which does not list untracked files. The synthetic base can therefore contain the new file as well. The laptop picker explicitly adds [untracked files](/src/forge/fasttest.py:395), so the box can skip a test that the laptop selects.
   Gain 4, Work 2, Harm 3
   Disposition: cut - `changes.txt` adds untracked, not ignored files as `A`; proved in `test_2`.

9. Blocking: A newly committed file has no base version for the prescribed upload.
   Raise: Plan gap
   Case: normal use - a change adds a tracked source or test file.
   [SHIP](/plans/FORGE-PROVIDER-2.md:74) requires `git show <base>:<path>` for every changed path. That command fails for an added file because it does not exist at the base. The named test does not cover a committed addition.
   Not done: item 2 must handle the working tree of a normal change.
   Gain 4, Work 2, Harm 3
   Disposition: cut - an `A` path has no `base/` file and the box removes it from the first commit; proved in `test_2`.

10. Blocking: The synthetic commits lose the proof list used to select close tests.
    Raise: Functional
    Case: normal use - close’s proof list names an unchanged test that must run.
    [SHIP](/plans/FORGE-PROVIDER-2.md:76) recreates two commits without the original commit messages. The picker obtains named tests from [proof entries](/src/forge/fasttest.py:842), which read the worker’s [commit message](/src/forge/review.py:771). The laptop’s later proof check cannot make a test run after the box omitted it.
    Not done: item 5 requires the laptop run’s result.
    Gain 3, Work 2, Harm 3
   Disposition: cut - the laptop sends `proof_tests` and the branch name in the recipe, and the box repo uses a branch named like the laptop's; proved in `test_2`.

11. Blocking: A repo whose default branch is not `main` cannot use the reconstructed checkout.
    Raise: Functional
    Case: normal use - a repo’s default branch is `master`.
    [SHIP](/plans/FORGE-PROVIDER-2.md:76) creates `refs/remotes/origin/<default>` but does not set `origin/HEAD`. Forge’s [default-branch lookup](/src/forge/repo.py:442) then falls back to `main`, and [forge test](/src/forge/fasttest.py:359) refuses the missing `origin/main`.
    Not done: item 5 requires a box run to return the test result.
    Gain 4, Work 1, Harm 3
   Disposition: cut - the box sets `origin/HEAD` as well as `origin/<default>`; proved in `test_2` on a `master` repo.

12. Blocking: The recipe does not pin the effective test base.
    Raise: Plan gap
    Case: normal use - a work branch is behind the default branch.
    [ROUTE](/plans/FORGE-PROVIDER-2.md:64) names a “base commit,” while [SHIP](/plans/FORGE-PROVIDER-2.md:74) diffs it directly. The laptop’s [test command](/src/forge/review.py:374) uses the merge base. Using the default branch’s tip instead changes the reconstructed diff and test selection; the planned comparison does not cover a diverged branch.
    Gain 3, Work 2, Harm 3
   Disposition: cut - the recipe carries `merge_base`, the id `review.close_test` computes after the merge handling, and the diff uses it; proved in `test_2` on a branch behind the default branch.

13. Blocking: The first box test takes all four test slots.
    Raise: Not done
    Case: normal use - two tests are reserved on one new box.
    [ROUTE](/plans/FORGE-PROVIDER-2.md:67) makes four slots available and assumes `worker_env` supplies a two-processor cap. The box starts `forge test` directly, and [machine.join](/src/forge/machine.py:309) allocates all available slots when that environment value is absent. The second test waits.
    Not done: item 4 requires two runs to fit on a box.
    Gain 4, Work 1, Harm 3
   Disposition: cut - in a box a run's own allocation is at most 2 processors, so two runs both start; proved in `test_1`.

14. Blocking: A fresh box cannot run Forge’s TypeScript starter tests.
    Raise: Functional
    Case: normal use - a generated TypeScript app sends a test to a fresh box.
    [GUEST](/plans/FORGE-PROVIDER-2.md:90) installs Ubuntu 24.04’s `nodejs`, which is [Node 18](https://packages.ubuntu.com/noble/nodejs). The starter requires [Node 24](/src/forge/templates/starter/package.json:5), and its [test script](/src/forge/templates/starter/scripts/test.mjs:3) imports `globSync`, added in [Node 22](https://nodejs.org/api/fs.html#fsglobsyncpattern-options). The run is reported as a test failure rather than preparation failure.
    Gain 4, Work 2, Harm 3
   Disposition: cut - the box installs Node at the repo's `NodeMajor` from nodejs.org with a checksum, and `ready` needs the right major; proved in `test_4` and `test_3`.

15. Blocking: A lost result after a failing test causes the test to run again.
    Raise: Not done
    Case: normal use - a test fails, then its result upload fails.
    [RUN](/plans/FORGE-PROVIDER-2.md:97) treats a failed command with no uploaded result as a reason to rerun on the laptop. That state cannot distinguish a preparation failure from a test failure followed by an upload failure.
    Not done: item 5 says a failing test never sends the run back to the laptop.
    Gain 4, Work 2, Harm 3
   Disposition: cut - the box prints a `FORGE_RESULT` line before it uploads, and a run with that line is returned as the tests' result and never rerun; proved in `test_5`.

16. Blocking: The no-place fallback cannot meet the plan’s own confirmation rule.
    Raise: Plan gap
    Case: normal use - all box places are occupied.
    [RUN](/plans/FORGE-PROVIDER-2.md:97) requires a terminal command status or an ended instance before fallback. A `none` claim has neither a command nor an instance to check, although [item 5](/plans/FORGE-PROVIDER-2.md:36) requires an immediate laptop run.
    Gain 4, Work 1, Harm 3
   Disposition: cut - a `none` or `old` answer, a failed claim and a box that was never ready start nothing, so they fall back at once; only a sent command needs a confirmed end; proved in `test_5`.

17. Blocking: The specified setup policy omits authorization for the command document.
    Raise: Test
    Case: normal use - a developer uses the shipped least-privilege policy.
    [SETUP](/plans/FORGE-PROVIDER-2.md:83) specifies `ssm:SendCommand` for tagged instances, but the [AWS policy requirements](https://docs.aws.amazon.com/systems-manager/latest/userguide/run-command-setting-up.html) also require authorization for the Systems Manager document. The planned fake does not prove that the shipped policy can send `AWS-RunShellScript`, so every real box run can be refused.
    Not done: item 5 requires a working box test run.
    Gain 4, Work 2, Harm 3
   Disposition: cut - `ssm:SendCommand` is allowed on both the `AWS-RunShellScript` document and the tagged instances, and story 1's policy simulation checks each action; proved in `test_3`.

18. Blocking: SETUP must prove laptop fallback before any task owns test routing.
    Raise: Plan gap
    Case: normal use - SETUP finishes and runs its required test before ROUTE starts.
    [SETUP’s test](/plans/FORGE-PROVIDER-2.md:84) must show an old stack sends the test to the laptop, but [ROUTE](/plans/FORGE-PROVIDER-2.md:117) owns the first hook in `review.test_run` and waits for SETUP. The current [test-run path](/src/forge/review.py:404) has no AWS routing to exercise.
    Gain 3, Work 1, Harm 3
   Disposition: cut - SETUP's test now checks the old-stack line through `status` and the update to version 2; the stay-on-the-laptop case moved to ROUTE's `test_1`, which owns the hook.

Not checked: a live AWS run. I skipped `forge next` because it can change repository files.
