---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-28T04:29:11.488096+00:00
seconds: 1058.094
read_hash: 3cb445aafaae236807e779afa68164c5ab3a7fbe
round: 2
passed: no
doc_seen: 3cb445aafaae236807e779afa68164c5ab3a7fbe
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 932eb3183633ceadff48ba5020fadef1e29bd65e
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21ff9-89ae-7901-913c-09e951d37fcb
session:
loop_choice: accept
loop_reason: Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details
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

## Round 2

19. Blocking: A fork’s code can pass the checkout check and read approved test files.
    Raise: Security  
    Case: normal use - a maintainer checks out a public fork’s pull request in the upstream clone and runs its tests.  
    [SHIP](/plans/FORGE-PROVIDER-2.md:74) checks only the `origin` repository ID. The upstream clone can have that ID while its checked-out branch contains fork code. The box then gives that code the approved files and internet access, contrary to the assumption that nobody outside the repo can reach a box. [GitHub CLI supports checking out pull requests locally.](https://cli.github.com/manual/gh_pr_checkout)  
    Gain 4, Work 3, Harm 4
   Disposition: keep - Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details

20. Blocking: A stale default-branch ref can send work to AWS after boxes are turned off.
    Raise: Security  
    Case: normal use - a teammate has not fetched since `aws_tests = false` merged.  
    [ROUTE](/plans/FORGE-PROVIDER-2.md:62) reads the locally stored default ref without a network check. It can therefore see the old `true` value and upload the teammate’s working tree while the stack still exists.  
    Not done: item 1 requires the default branch’s setting to control routing.  
    Gain 4, Work 3, Harm 4
   Disposition: keep - Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details

21. Blocking: An approved test file can remain in Docker’s build cache after the run ends.
    Raise: Security  
    Case: normal use - a starter app builds its Docker image while an approved ignored fixture is in the working tree.  
    The starter’s [Dockerfile](/src/forge/templates/starter/Dockerfile:4) copies the tree into a build stage. An ignored fixture need not match the starter’s [Docker exclusions](/src/forge/templates/skeleton/.dockerignore:1). [SHIP](/plans/FORGE-PROVIDER-2.md:77) deletes the run folder, but Docker’s [build cache is separate](https://docs.docker.com/reference/cli/docker/builder/prune/). The file can remain on the box after the run, even without a concurrent run.  
    Not done: item 2 promises deletion of the approved files when the run ends.  
    Gain 4, Work 3, Harm 4
   Disposition: keep - Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details

22. Blocking: A repo without Node can never make its box ready.
    Raise: Functional  
    Case: normal use - a Python or Go repo sends a test to a new box.  
    [SETUP](/plans/FORGE-PROVIDER-2.md:83) sets `NodeMajor` to zero for a repo without Node. [GUEST](/plans/FORGE-PROVIDER-2.md:91) installs no Node in that case but still requires `node` to run with that major before declaring the box ready. Forge supports [Python and Go repos](/src/forge/init.py:72).  
    Not done: item 4 requires a usable box for these runs.  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details

23. Blocking: Forge is installed for root but invoked as a different user.
    Raise: Functional  
    Case: normal use - a fresh box starts its first test.  
    [GUEST](/plans/FORGE-PROVIDER-2.md:91) installs Forge as root using [the existing install command](/src/forge/sync.py:149). By default, `uv tool install` places the tool under that user’s home; [SHIP](/plans/FORGE-PROVIDER-2.md:77) then invokes it as a new run user. The root-only readiness check can pass while that user cannot run Forge. [uv storage locations](https://docs.astral.sh/uv/reference/storage/)  
    Not done: item 5 requires the box to run and return the tests.  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details

24. Blocking: The shipped AWS policy cannot perform the new secret-version update.
    Raise: Functional  
    Case: normal use - a developer uses the documented least-privilege permission set and runs `forge lanes --aws files`.  
    [SHIP](/plans/FORGE-PROVIDER-2.md:76) requires `UpdateSecretVersionStage` after each write, but [SETUP’s policy](/plans/FORGE-PROVIDER-2.md:84) grants only `PutSecretValue` for the test-files secret. AWS requires [a separate permission](https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_UpdateSecretVersionStage.html), so the command fails after writing the secret.  
    Not done: item 2 requires approved files to be managed through `files`.  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details

25. Blocking: The box is not given the Node version it must install.
    Raise: Plan gap  
    Case: normal use - a Node repo starts a new box.  
    [SETUP](/plans/FORGE-PROVIDER-2.md:83) stores `NodeMajor` as a stack parameter, and [GUEST](/plans/FORGE-PROVIDER-2.md:91) needs it before readiness. The inputs [PLACES passes to the guest](/plans/FORGE-PROVIDER-2.md:89) do not include it, and no other handoff is specified. The separate fake tests can pass without proving that handoff.  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; the 7 open notes (#19-25) become must-fix lines in the covered Done-when details

26. Advisory: The required untracked-file comparison cannot pass as written.
    Raise: Test  
    [SHIP’s test](/plans/FORGE-PROVIDER-2.md:79) requires an untracked test to be committed as an addition in the synthetic box repo and also requires its `git diff --name-status` to equal the laptop’s. The laptop’s `git diff` omits untracked files; Forge’s [picker lists them separately](/src/forge/fasttest.py:395).  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

27. Advisory: An approved file ignored by local Git settings can make a box close fail.
    Raise: Functional  
    [SHIP](/plans/FORGE-PROVIDER-2.md:76) accepts files ignored by `--exclude-standard`, including a developer’s global ignore rules. The reconstructed repo and new run user do not receive those rules, so such a file can appear untracked after the secret is written. The existing [close dirty check](/src/forge/review.py:443) then refuses it, although the laptop checkout is clean.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

28. Advisory: A Node major does not preserve an exact version selected by the repo.
    Raise: Functional  
    [SETUP](/plans/FORGE-PROVIDER-2.md:83) retains only the major version, while [the generated CI](/src/forge/prcheck.py:283) can use an exact `.nvmrc` or `.node-version`. Two repos requiring different releases within the same major become indistinguishable, so the box can run a different runtime and give a different result.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

29. Advisory: The planned guide omits a step that turn-off now requires.
    Raise: Not done  
    [The turn-off rule](/plans/FORGE-PROVIDER-2.md:104) refuses while `test_runner = "forge-aws"` remains on the default branch. The [guide instructions](/plans/FORGE-PROVIDER-2.md:105) repeat the old order without removing it, so a repo using both features reaches that refusal.  
    Gain 2, Work 1, Harm 1
   Disposition: keep - below the bar (live with)

30. Advisory: The planned secret read is not proven against the new stage restriction.
    Raise: Test  
    [SETUP](/plans/FORGE-PROVIDER-2.md:83) restricts reads using `secretsmanager:VersionStage`, but [SHIP](/plans/FORGE-PROVIDER-2.md:77) does not specify sending `AWSCURRENT` in the read request. AWS has documented a [denied implicit-stage request](https://github.com/aws/aws-cli/issues/5031); the planned tests check the policy and fake read separately. A live AWS run was not checked.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)
