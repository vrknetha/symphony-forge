---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-22T12:07:11.629806+00:00
seconds: 540.645
read_hash: 7be6b6c41660a4ed4870f03db52d8ed3eecd657d
round: 3
passed: no
doc_seen: 7be6b6c41660a4ed4870f03db52d8ed3eecd657d
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: c4dd5af64a54577e1454fa96853ffe269a4c2858
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a202fd-91c8-79c1-b860-c6669f741926
session:
loop_choice: split
loop_reason: Owner chose on 22 Nov 2026: split full JavaScript run proof (Vitest and Playwright report reading, notes 27 to 30) into its own item; this story proves Python tests fully and only checks that JavaScript Done-when tests are named on the branch
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

1. Blocking: Data loss: Replay can erase uncommitted code.
   Raise: Data loss. [The plan](/plans/FORGE-TESTQUAL-1.md:261) restores changed code from Git, then restores `HEAD`. Close can reach its test run with uncommitted edits; [the cache check](/src/forge/review.py:538) merely disables caching for a dirty checkout.
   Case: normal use - a person makes an uncommitted edit to a changed code file before close. Replay overwrites it.
   Adds work: protect uncommitted code before replay; F 2 x H 3 = 6; 2 x C = 4.
   Gain 5, Work 2, Harm 5
   Disposition: cut - replay now runs in a temporary worktree outside the repo at the fix base plus the head's committed test files; the item's checkout and uncommitted work are never read or written (item 5 details).

2. Blocking: Replay does not restore a fix that deletes a code file.
   Raise: Functional. After the first restore in [the plan](/plans/FORGE-TESTQUAL-1.md:261), a file deleted by the fix exists in the worktree but is absent from both `HEAD` and the index. The final restore cannot match it to `HEAD`, so it leaves the old file behind and can fail the command.
   Case: normal use - a fix removes an obsolete code file and changes a test.
   Gain 4, Work 2, Harm 3
   Disposition: cut - in the temporary worktree, code stays at the fix base, so deleted files exist there and nothing needs restoring; new case `deletes-a-file`.

3. Blocking: Existing repos with their own CI check bypass both new close checks.
   Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:80) assumes CI calls `forge test --change`. [The workflow generator](/src/forge/prcheck.py:304) emits that job only when `checks` includes `tests`; otherwise it removes the job. Close also skips local tests in CI mode.
   Case: normal use - an existing repo names its own required CI check instead of `tests`. Neither proof validation nor replay runs.
   Gain 5, Work 4, Harm 3
   Disposition: cut - repos whose checks lack `tests` get the name check in `forge-pr-check` (`ran=False`); the plan, What changes and Accepted limits say exactly what they do not get, with owner question 1.

4. Blocking: A proof-only commit can bypass the CI proof check.
   Raise: Not done. [CI reuses an earlier result](/src/forge/templates/review-tests.py:207) when the file diff is empty, so it skips `forge test --change`. [Existing tests](/tests/test_reviews_receive_done_when_proof.py:96) explicitly support commits that change only the proof list.
   Case: normal use - a proof-only commit omits a covered item after an earlier green run. CI reuses that run without checking the new list.
   Gain 4, Work 2, Harm 2
   Disposition: cut - review-tests.py reuses an earlier CI run only when its head has the same Proof list paragraph; synced to existing repos.

5. Blocking: A corrected proof list can remain stuck on an old local test result.
   Raise: Not done. [The cached-pass key](/src/forge/review.py:538) uses the command and file tree, not the proof-list commit message. [The plan](/plans/FORGE-TESTQUAL-1.md:152) checks cached results before selecting the newly named test.
   Case: normal use - a proof-only commit names a different existing test that the cached run did not select. Repeated closes reuse the same result and keep refusing it.
   Gain 4, Work 2, Harm 2
   Disposition: cut - passed_record's key adds the Proof list text, so a proof-only commit reruns and a cache hit is the same files and list; new case `proof-only-commit`.

6. Blocking: Later Vitest runs overwrite earlier proof in the starter.
   Raise: Not done. [The starter test script](/src/forge/templates/starter/scripts/test.mjs:65) runs affected projects separately, while their [Vitest configuration](/src/forge/templates/starter/apps/web/vitest.config.ts:18) gives them the same JUnit output file. The plan reads that file only after the command ends.
   Case: normal use - a change affects two tested projects. The later run replaces the earlier report, and close says the earlier named test did not run.
   Gain 4, Work 2, Harm 3
   Disposition: cut - the starter's web Vitest config writes `formats-${process.pid}.xml`, and the check reads every fresh JUnit file.

7. Blocking: Reused Vitest tests are not added to test selection.
   Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:188) adds only named pytest tests. [The existing Vitest path](/src/forge/fasttest.py:325) uses `--changed`.
   Case: normal use - an unchanged, black-box Vitest test proves a change without importing the changed file. Selection omits it, and close refuses the valid proof as not run.
   Gain 4, Work 2, Harm 2
   Disposition: cut - close_tests runs Proof-list Vitest files the `--changed` run missed in one more `vitest run <files>`; starter projects run all their tests.

8. Blocking: A named pytest test can pass the proof check without running.
   Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:172) reports “did not run” for Python only when a pytest results header exists. The [Python starter selector](/src/forge/templates/starter-python/scripts/test.mjs:62) can run web checks without starting pytest.
   Case: normal use - a proof list names a Python integration test, but the selected command runs no pytest. Close accepts the entry without evidence that it ran.
   Gain 4, Work 2, Harm 3
   Disposition: cut - a `.py` name with no result is "did not run" in every ungrouped run, since Forge's hook loads into every pytest; no header condition.

9. Blocking: A skipped proof case can be hidden by another passing case.
   Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:170) refuses skipped results only when *all* matches are skipped. It also permits a whole file or parametrized test as a proof name.
   Case: normal use - the case proving the Done-when line is skipped while another case in the named file passes. Close accepts the entry.
   Gain 3, Work 2, Harm 2
   Disposition: cut - any skipped, xfail or xpass match now refuses, even beside passing cases, and asks for the exact case; `skipped` case uses a mixed file.

10. Blocking: The plan both requires changed tests and accepts unchanged reused tests.
    Raise: Plan gap. [Done-when item 2](/plans/FORGE-TESTQUAL-1.md:38) requires refusal when the named test is not in the change, but [the reuse case](/plans/FORGE-TESTQUAL-1.md:205) requires Ready for an unchanged test. The current [proof reader](/src/forge/review.py:763) checks whether the branch has the file, not whether the change modifies it.
    Case: normal use - a builder reuses an existing test.
    Gain 4, Work 1, Harm 2
   Disposition: cut - Done-when 2 and the message now say "not on the branch"; a reused unchanged test passes that check.

11. Blocking: Replay can keep the original CI shard instead of running all named tests.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:254) resets group environment variables for replay, but [test execution](/src/forge/review.py:390) has already expanded the command’s group placeholders.
    Case: normal use - a repo uses `vitest run --shard={group}/{groups}` and the named test is outside group 1. Replay keeps `--shard=1/N`, reports no result, and warns even if the test passes on old code.
    Gain 4, Work 2, Harm 2
   Disposition: cut - replay rebuilds the command with `review.close_test` in the copy and fills it with FORGE_GROUPS=1 and FORGE_GROUP=1, so a `{group}` shard runs all files.

12. Blocking: The commit check misses the starter’s API Vitest files.
    Raise: Not done. [The planned filename patterns](/plans/FORGE-TESTQUAL-1.md:214) match `*.test.*` and `*.spec.*`, but [the starter](/src/forge/templates/starter/apps/api/vitest.config.ts:7) runs `*.e2e-spec.ts`.
    Case: normal use - a builder adds an always-true assertion to an API test such as `environment.e2e-spec.ts`. The hook does not inspect it.
    Gain 4, Work 2, Harm 2
   Disposition: cut - the commit check uses `repo.TEST_PATHS` with JS and TS extensions, which covers `apps/api/test/*.e2e-spec.ts`; new case added.

13. Blocking: Multiline JavaScript assertions evade the commit check.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:224) matches JavaScript one line at a time. [Starter tests](/src/forge/templates/starter/apps/web/e2e/served-app.spec.ts:9) already split `expect(...)` and its matcher across lines.
    Case: normal use - an always-true `expect(value)` followed by `.toBe(value)` on the next line commits.
    Gain 3, Work 2, Harm 2
   Disposition: keep - Accepted limits now states the one-line JavaScript scope, and Done-when 3 says "written on one line"; multi-line parsing is cut as fragile (coordinator's guidance).

14. Blocking: Merge commits are exempt from the promised assertion check.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:214) skips the hook whenever `MERGE_HEAD` exists, while [close normally merges default-branch changes](/src/forge/close.py:753).
    Case: normal use - a conflict resolution adds an always-true assertion. Its merge commit is accepted.
    Gain 3, Work 2, Harm 2
   Disposition: keep - Accepted limits now states that merge commits skip the check: they bring default-branch tests already checked at their own commit, and checking them would block on others' code.

15. Blocking: A supported nested test title fails the source check.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:168) requires the entire named case to occur as a whole word in the source. The starter’s [nested Vitest suite](/src/forge/templates/starter/libs/shared/util/src/format.test.ts:7) writes the suite and test titles separately.
    Case: normal use - the proof names the full `suite > test` title. It exists in the report but not as one string in the file, so close refuses it.
    Gain 3, Work 2, Harm 2
   Disposition: cut - for a JavaScript title the source check looks for its last ` > ` part only; the run results still match the full title.

16. Blocking: The first test in a new repo has no valid closest-test choice.
    Raise: Plan gap. [The required line form](/plans/FORGE-TESTQUAL-1.md:110) requires a new test to name a closest existing test, while [a new repo without a starter](/src/forge/init.py:228) can start with none. The plan defines no choice for that state.
    Case: normal use - the builder adds the repo’s first test.
    Gain 4, Work 1, Harm 2
   Disposition: cut - the decision form adds `new; closest none; proves <outcome>` for a repo with no near test.

17. Blocking: The lint task depends on a test its prerequisite does not provide.
    Raise: Plan gap. [This plan](/plans/FORGE-TESTQUAL-1.md:246) says to extend `test_2_a_module_mock_in_a_test_fails_lint`; [the prerequisite plan](/plans/FORGE-FASTCI-1.md:135) creates `test_1` and does not specify that `test_2`.
    Case: normal use - LINT starts after its stated prerequisite and cannot extend the named test.
    Gain 4, Work 1, Harm 1
   Disposition: keep - factually wrong: the approved FORGE-FASTCI-1 plan on story/FORGE-FASTCI-1 (Done-when 2 details and the OXLINT Tests cell) adds `test_2_a_module_mock_in_a_test_fails_lint`; main holds an older copy. The plan now cites it.

18. Blocking: Existing proof-list tests require the instructions this plan replaces.
    Raise: Plan gap. [The existing test](/tests/test_reviews_receive_done_when_proof.py:12) requires the old `missing` and pytest-only wording. [The plan](/plans/FORGE-TESTQUAL-1.md:132) replaces that wording but does not name the test for an update.
    Case: normal use - PROOF changes the shipped brief and guide, and the existing suite fails on their former text.
    Gain 4, Work 2, Harm 2
   Disposition: cut - PROOF's Scope and item 1 details now update `WORKER_RULE` and `NAMES_RULE` in tests/test_reviews_receive_done_when_proof.py.

## Round 2

19. Blocking: Replay copies tests from the old commit.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:316) creates the temporary worktree at the fix base, then runs `git checkout HEAD -- <test files>` inside it. There, `HEAD` is still the fix base: an added test cannot be checked out, and a changed test is restored to its old contents.
    Case: normal use - a fix adds a regression test, so replay cannot run that test against the old code.
    Gain 5, Work 2, Harm 3
   Disposition: cut - replay reads the fix head's sha in the item's checkout first and runs `git checkout <head> -- <test files>` in the copy, whose own HEAD is the fix base.

20. Blocking: The new CI name check has no pull-request head to inspect.
    Raise: Plan gap. [The pinned `proof.check` interface](/plans/FORGE-TESTQUAL-1.md:121) receives no head commit. [The CI workflow](/src/forge/prcheck.py:149) checks out the base and supplies the pull-request head separately; the current [proof reader](/src/forge/review.py:703) defaults to the checkout’s `HEAD`. The planned own-CI test covers only a missing proof list.
    Case: normal use - a pull request adds a test and names it in its proof list; the planned check has no specified way to read either from the pull-request head.
    Gain 5, Work 2, Harm 3
   Disposition: cut - `proof.check` takes `head`; `pr_check` passes its `--head` commit, and the check reads the Proof list and named files from that commit; the `own-ci-check` case now also passes a head that adds and names a test the base lacks.

21. Blocking: The new report filenames break starter smoke CI.
    Raise: Plan gap. [The plan](/plans/FORGE-TESTQUAL-1.md:224) replaces `formats.xml` with a process-specific filename, but existing [live starter tests](/tests/test_database_money.py:45) still require `formats.xml`. Changing the starter config selects those tests in [smoke CI](/scripts/smoke_select.py:38).
    Case: normal use - PROOF changes the starter config and its pull request runs the required starter smoke job; the test report it expects is missing.
    Gain 5, Work 3, Harm 3
   Disposition: cut - the config rename is dropped; `formats.xml` keeps its name and content, and both starters' `test.mjs` copy each fresh report to `test-results/runs/`; builder question 4 says to run starter smoke's live tests.

22. Blocking: The Python starter still omits reused Vitest tests.
    Raise: Not done. The fix for finding 7 says [starter scripts run every test in an affected project](/plans/FORGE-TESTQUAL-1.md:228), but the [Python starter](/src/forge/templates/starter-python/scripts/test.mjs:68) still runs Vitest with `--changed`. Its `fast_test` uses that script, so the added selection in `fasttest.close_tests` does not cover it.
    Case: normal use - an unchanged web test proves a change without importing the changed file; other web tests run, but close refuses the omitted proof as not run.
    Gain 4, Work 2, Harm 2
   Disposition: cut - the Python starter's `test.mjs` runs the `FORGE_PROOF_TESTS` web files in one more Vitest run after its `--changed` run.

23. Blocking: The extra Vitest run can overwrite proof from the first run.
    Raise: Not done. [The new selection rule](/plans/FORGE-TESTQUAL-1.md:231) runs missed proof files in a second Vitest invocation, but reads JUnit only after the command. A normal Vitest configuration writes both invocations to one report, as the [starter API config](/src/forge/templates/starter/apps/api/vitest.config.ts:10) does.
    Case: normal use - one proof test runs in the changed selection and another in the added run; the second report replaces the first, so close refuses the first as not run.
    Gain 5, Work 2, Harm 3
   Disposition: cut - each Vitest run's report now survives: the starters copy `formats.xml` after every command, and Forge's extra run writes its own `test-results/runs/forge-proof.xml`; new case `vitest-two-runs`.

24. Advisory: CI reuse cannot identify the active proof behind record commits.
    Raise: Plan gap. [The new comparison](/plans/FORGE-TESTQUAL-1.md:185) reads only each head commit’s message, while [Forge’s proof reader](/src/forge/review.py:703) searches past bookkeeping commits. Two record-commit tips have no proof paragraph whether the effective proof stayed the same or changed in a proof-only commit between them, so the prescribed comparison cannot distinguish those cases.
    Gain 3, Work 2, Harm 2
   Disposition: cut - CI reuse now compares the effective Proof list, the newest paragraph in each head's history after the base, skipping record-only commits as `commit_paragraph` does.

25. Advisory: An unrelated JUnit report turns the promised JavaScript warning into a refusal.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:207) treats any fresh JUnit file as evidence that a missing JavaScript result did not run. In a mixed repo, pytest can write [its own JUnit report](/src/forge/templates/starter-python/package.json:14) while Vitest writes none; close then refuses the Vitest proof instead of giving the promised warning.
    Gain 3, Work 2, Harm 2
   Disposition: cut - "did not run" for a JavaScript name now needs a JUnit file with a JavaScript case; a pytest JUnit report alone gives the warning.

26. Advisory: The review prompt claims run checks happened when they were skipped.
    Raise: Not done. [The prescribed prompt](/plans/FORGE-TESTQUAL-1.md:155) tells the reviewer that close has refused tests that did not run, failed or were skipped. The same plan [excludes those checks](/plans/FORGE-TESTQUAL-1.md:57) for repos with their own CI test check and warns when JavaScript reports are unavailable.
    Gain 3, Work 1, Harm 2
   Disposition: cut - the review text is now `$proof_checked`, filled with what close really checked in that repo (full check, or names only for repos with their own CI test check); new case `review-prompt`.

## Round 3

27. Blocking: A local test can pass using code that is not in the pull request.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:193) says results are for the current commit, but [close runs the test command in the working checkout](/src/forge/review.py:455). A dirty checkout disables the cache; it does not prevent the run.
    Case: normal use - committed code fails the named test, but an uncommitted edit makes it pass. Close can accept that result while the pull request still contains the failing code.
    Gain 5, Work 3, Harm 3
   Disposition: cut - on the pytest path, close's local check now refuses a checkout with uncommitted changes (case `uncommitted-edit`); the JavaScript side moves to the Split out follow-up.

28. Blocking: The extra Vitest report can be written outside the directory close reads.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:247) gives the extra run a relative report path, but Vitest resolves it against its configured root. The [starter’s web config](/src/forge/templates/starter/apps/web/vitest.config.ts:6) sets that root to `apps/web`; close reads reports under the repository’s `test-results/`.
    Case: normal use - a repo runs Vitest directly with that web config and names an unchanged test. The extra run writes under `apps/web/test-results/`, so close cannot see its result.
    Gain 4, Work 2, Harm 2
   Disposition: cut - JavaScript report reading and the extra Vitest run are removed by the owner's split; the case is listed under Split out.

29. Blocking: Two extra Vitest runs overwrite each other’s reports.
    Raise: Not done. [The revised plan](/plans/FORGE-TESTQUAL-1.md:247) assigns every extra run `test-results/runs/forge-proof.xml`. The existing [test command handler](/src/forge/fasttest.py:321) supports more than one Vitest part, and close reads the reports after the command finishes.
    Case: normal use - a repo has separate unit and integration Vitest commands, each with a reused proof test. The second extra run replaces the first report, so close says the first test did not run.
    Gain 4, Work 2, Harm 2
   Disposition: cut - the extra Vitest runs are removed by the owner's split; the case is listed under Split out.

30. Blocking: A Playwright proof is passed to Vitest.
    Raise: Functional. [The plan](/plans/FORGE-TESTQUAL-1.md:131) puts both Vitest and Playwright files in `FORGE_PROOF_TESTS`, then [passes those files to each extra Vitest run](/plans/FORGE-TESTQUAL-1.md:252). Forge supports [commands containing both runners](/tests/test_windows_worker_skips_browser_tests.py:122).
    Case: normal use - a mixed command names a Playwright `*.spec.ts` as proof. A Vitest configuration that discovers that file tries to load its Playwright `test()` outside Playwright and fails before the browser command runs.
    Gain 5, Work 2, Harm 3
   Disposition: cut - FORGE_PROOF_TESTS and the extra Vitest run are removed by the owner's split; the case is listed under Split out.

31. Advisory: CI and close use different rules for finding the effective proof.
    Raise: Plan gap. [The revised CI lookup](/plans/FORGE-TESTQUAL-1.md:198) skips `.factory/` and `plans/spotted/`, while [close skips all of `plans/`](/src/forge/review.py:40). If a `plans/ideas.md` commit carries proof B after proof A, and an empty commit then repeats B, CI sees B at both heads while close changes from A to B. CI can reuse the run that checked A.
    Gain 3, Work 1, Harm 2
   Disposition: cut - CI reuse now skips the same record-only commits as close, every path under `review.BOOKKEEPING` (`.factory/` and `plans/`).

32. Advisory: A recovered timeout remains a failed proof result.
    Raise: Functional. [Close retains both attempts’ pytest results](/src/forge/review.py:468), and its [existing retry test](/tests/test_close_retries_failed_files.py:105) expects Ready when a timeout passes on retry. [The new proof rule](/plans/FORGE-TESTQUAL-1.md:219) refuses any matching failure, including the first attempt.
    Gain 3, Work 2, Harm 2
   Disposition: cut - pytest results now come from each test's last attempt (lines after the last `fasttest.RETRY_HEADER` for a retried file), so a retry that passes counts as passed; new case `retry-recovered`.

33. Advisory: The review is told checks have finished while they are still running.
    Raise: Not done. [The revised prompt](/plans/FORGE-TESTQUAL-1.md:168) says close has already refused invalid test results. In the local-test flow, [close starts tests alongside the review](/src/forge/close.py:354) and waits for their result afterward, so that statement is not established when the reviewer reads it.
    Gain 3, Work 1, Harm 2
   Disposition: cut - `$proof_checked` now says close refuses when its test run finishes and that the run may still be going during the review.

34. Advisory: A reused browser test can reach a project the starter does not select.
    Raise: Not done. [The plan](/plans/FORGE-TESTQUAL-1.md:254) says a test in an unaffected project cannot reach the change. The starter’s [browser test calls the API](/src/forge/templates/starter/apps/web/e2e/served-app.spec.ts:13), while an [API-only change does not select the browser tests](/tests/test_affected_ts_starter.py:105). Naming that existing browser test can therefore make close refuse valid proof as not run.
    Gain 3, Work 2, Harm 2
   Disposition: cut - JavaScript run proof is removed by the owner's split; the case is listed under Split out.
