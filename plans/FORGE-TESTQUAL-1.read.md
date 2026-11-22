---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-22T11:34:16.264774+00:00
seconds: 754.028
read_hash: f6335d4d359ee48d2dc2efa9fda21d28144fdc6c
round: 1
passed: no
doc_seen: f6335d4d359ee48d2dc2efa9fda21d28144fdc6c
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a202fd-91c8-79c1-b860-c6669f741926
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
