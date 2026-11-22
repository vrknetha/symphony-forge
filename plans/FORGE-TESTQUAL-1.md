# Make agent-written tests prove real behaviour

3 parts · Risks: none one-way; six accepted limits · New moving parts: none

## What changes for you

- Before a builder adds a test, the builder names the closest test that already exists. The builder then reuses that test, extends it, or adds a new test. A new test says which outcome no existing test proves. The review reports a new test that does not say this. (Source: the owner's decision, 22 Nov 2026)
- Each Done-when line names the test that proves it, in the proof list that the builder writes in the last commit. For a pytest test, close checks that the test is on the branch, ran, passed and was not skipped. For a Vitest or Playwright test, close checks only that the test is on the branch; proof that it ran comes in a later item. The review checks that the test's assertion proves the line. A line that changes only settings, docs or tests can name a check in place of a test. (Source: the owner's decision, 22 Nov 2026)
- Git refuses a commit when a test it adds has a check that is always true, such as `assert True` or `expect(x).toBe(x)`, in pytest, Vitest and Playwright tests. (Source: the owner's decision, 22 Nov 2026)
- A new pytest test with no assertion gets a warning at commit, because many good tests check the result in a helper. In a new starter app, lint fails on a Vitest or Playwright test with no assertion. (Source: the owner's decision, 22 Nov 2026)
- For a fix, close also runs the fix's new or changed pytest test on the code before the fix, in a separate temporary copy of the repo. There the test must fail, and on the new code it must pass. When the test cannot start on the old code, for example because it imports a function that the fix adds, close gives a warning and the review judges the test. Your own files and uncommitted work are never touched. The same check for Vitest and Playwright tests comes in a later item. (Source: the owner's decision, 22 Nov 2026)
- What each repo gets: a new repo gets all of this at setup. An existing repo gets it when it upgrades Forge and runs sync. In an existing repo whose CI runs its own test check in place of Forge's, Forge sees no test results, so it checks only that each Done-when line names a test that is on the branch; the run check and the old-code check need Forge's test check. An item that is open during the upgrade must write its proof list in the new form at its next close.
- Not in this story: proof that Vitest and Playwright tests ran (a later item, below), mutation testing (later), a minimum number of assertions, a limit on new tests.

Design: none (no screen changes)

## Why

Agents add many weak tests. They add a new test where an existing test already fits, they write
tests with weak assertions or none, and they write tests that follow the code's structure in place
of the product's scenarios. Today the only guard is the test-audit rules in the worker brief and
the model review. Both are instructions, and nothing checks them. A weak test costs twice: it
does not catch the bug it was written for, and every later change must keep it passing.

The evidence points the same way. Meta's TestGen-LLM extended existing test classes, and engineers
accepted 73% of its suggestions (https://arxiv.org/abs/2402.09171). In SWE-Mutation (ACL 2026),
generated test suites caught 71% of simple code faults but only 40% of more complex ones
(https://aclanthology.org/2026.findings-acl.1976/). OpenAI's 2026 audit of coding evaluations found
tests that accepted incomplete fixes (https://openai.com/index/separating-signal-from-noise-coding-evaluations/).
Vitest can check that an assertion ran (https://vitest.dev/api/expect.html), and Playwright tells
authors to test what the user sees (https://playwright.dev/docs/best-practices). Forge's own suite
shows where to block and where to warn: of its 1,752 test functions, none has an always-true check,
and 90 (5%) check their result only in a helper.

## Done when

1. **The worker instructions tell each builder to name the closest existing test and to choose reuse, extend or new, and the review reports a new test that does not say which outcome no existing test proves.**
2. **Close refuses a task or fix when one of its Done-when lines names no test or names a test that is not on the branch, or when a named pytest test did not run, failed or was skipped.**
3. **A commit that adds an always-true check to a pytest test, or an always-true check written on one line to a Vitest or Playwright test, is refused.**
4. **A new pytest test with no assertion gets a warning at commit, and a Vitest or Playwright test with no assertion fails lint in a new starter app.**
5. **Close refuses a fix whose new or changed pytest test passes on the code before the fix, and gives only a warning when that test cannot run on that code.**

## Risks

<!-- Each one-way step: deleting data, a destructive migration, a new vendor. -->

Risks: none one-way. Each part reverts with its pull request. No record changes form.

Accepted limits:
- For Vitest and Playwright tests, close checks only that the named test is on the branch. It does
  not check that the test ran or passed, and it does not run it on the code before a fix. The later
  item "Prove JavaScript Done-when tests ran (Vitest and Playwright reports)" adds that. Until then
  the review judges those tests.
- A fix's pytest tests run twice: once on the new code and once on the code before the fix, in a
  fresh temporary copy. The copy has no installed packages, so the test command must install what
  it needs, as `uv run` does. Where it cannot, the old-code run cannot start and close gives a
  warning for that fix, not a refusal.
- In CI with more than one test group (Forge's own repo uses six), each group sees only its own
  results, so there close cannot prove that a named test ran. It checks only that the named test
  passed where it ran. Named pytest tests are added to the test selection so that they run.
- An existing repo whose CI runs its own test check gets only the check that each Done-when line
  names a test on the branch. The run check and the old-code check need Forge's test check.
- The commit check reads a Vitest or Playwright assertion on one line only. An always-true check
  split over two lines, such as `expect(value)` with `.toBe(value)` on the next line, is not
  caught; the review still reads it.
- The commit check does not run on merge commits, because those bring in the default branch's
  tests, which were checked when they were committed.

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

Each new test file starts with `STORY = "FORGE-TESTQUAL-1"`, runs the forge command (or git, for
the commit hook) and never imports forge. One test per Done-when item, named `test_<n>_...`.
Close cases use the `env` fixture and helpers of `tests/test_close.py` (`start_fix`,
`start_approved_task`, `close`, `prompt`, `reviews`), `configure` from
`tests/test_testplace_settings.py` for a local-test repo, and `install_claude` and `calls` from
`tests/test_worker.py` for briefs. No test in this story runs Vitest or Playwright. All rules are
tested on a new repo only (Review rules).

**What the code does today.**
- The worker's last commit already carries a `Proof list:` paragraph that maps Done-when items to
  tests (`brief.md:816-822`, `skill.md:2224-2237`). `review.proof_list` (`review.py:740-794`)
  writes each named pytest test's result from close's run next to it, from the per-test results
  that Forge's pytest hook writes (`fasttest.py:553-661`, lines `<outcome> <node>`). Other names are
  `not checked`. Nothing refuses a missing or failed entry; only the model review judges it.
- Close runs tests through `review.test_run` (`review.py:387-523`), in the item's checkout, which
  may hold uncommitted edits. CI runs the same function through `forge test --change`
  (`prcheck.py:305`, `fasttest.py:340-375`), but only when `checks` names `tests`; otherwise the
  generated workflow has no tests job (`prcheck.py:494-497`) and only `forge-pr-check`
  (`prcheck.pr_check`, `:505`) runs Forge code in CI. In CI the checkout is a detached HEAD, so the
  branch comes from `GITHUB_HEAD_REF`.
- Close retries failed test files once and writes both attempts to the results file, the second
  after `fasttest.RETRY_HEADER` (`review.py:449-486`); `tests/test_close_retries_failed_files.py:105`
  expects Ready when the retry passes.
- Close reuses an earlier local pass keyed on the command and the committed files
  (`review.passed_record`, `:538`), and CI reuses an earlier run when only records changed
  (`templates/review-tests.py:195-207`). Neither key includes the Proof list, and
  `tests/test_reviews_receive_done_when_proof.py:96` shows that proof-only commits are normal.
- The worker brief and the review prompt both embed the test-audit skill's Authoring gate
  (`worker.py:767-768` in `design_context`, used by `brief.md:73` and `review.md:68`). The skill's
  source is `.codex/skills/test-audit/SKILL.md`; sync writes the `.claude` copy and bundles it.
- The brief lists "Existing tests that name a file or folder in your Scope" (`worker._existing_tests`),
  which is the builder's list of candidates for the closest test.
- `review.py`, `close.py` and `story.py` are at exactly 1,200 lines, the limit that
  `tests/test_rules.py::test_5_forge_stays_small` checks. PROOF moves `proof_list` and its helpers
  (`TEST_NAME`, `RESULT_WORDS`, `_ran`, about 60 lines) out of `review.py` into the new module, which
  makes room for the new calls. `close.py` changes only its three `review.proof_list` calls and its
  import line, so its line count does not change.
- The FORGE-FASTCI-1 OXLINT part (approved on `story/FORGE-FASTCI-1`, not yet built) turns on every
  Oxlint rule group as an error with the `vitest` plugin in both starters, and adds
  `tests/test_starter_lint_settings.py::test_2_a_module_mock_in_a_test_fails_lint` (its approved
  plan, Done-when 2 details). `vitest/expect-expect` is in the correctness group
  (https://oxc.rs/docs/guide/usage/linter/rules.html), so new starters get the TypeScript
  no-assertion rule from that part. This story adds no lint setting; LINT only proves it.

**Words this story pins.** PROOF commits these; REPLAY uses them.

- Module `src/forge/proof.py`: `proof_list(top, base, report=None)` (moved, same behaviour),
  `entries(top, item, commit) -> dict[str, list[str]]` (each covered Done-when key, `"1"` or
  `"Done when"`, to its named tests, or `["check:"]`), and
  `check(top, item, base, results, *, ran=True, head="HEAD") -> tuple[bool, list[str]]` (passed,
  message lines; `ran=False` does only the name checks; `head` is the commit whose Proof list and
  files it reads). `review.test_run` calls it on its closing path, and `prcheck.pr_check` calls it
  with `ran=False` and its `--head` commit, since that job checks out the base and has the pull
  request's commits only as data. With a `head` other than the checkout, the Proof list comes from
  `review.commit_paragraph(top, base, "Proof list:", head)` and each named file from
  `git show <head>:<path>`.
- Proof list line form, one or more per covered item:
  `- <n>: <test> (<decision>)` for a task (`- 1, 3: ...` covers two items) and
  `- Done when: <test> (<decision>)` for a fix. Regex:
  `^\s*(?:-\s*)?(?P<key>\d+(?:\s*,\s*\d+)*|Done when)\s*:\s*(?P<rest>.*)$`.
  `<test>` is a pytest node ID or file (the existing `TEST_NAME`), or a Vitest or Playwright file
  with an optional title in backticks: `` `apps/web/e2e/sign-in.spec.ts::signs in with a link` ``.
  `<decision>` is `reuse`, `extend <closest test>`, `new; closest <test>; proves <outcome>`, or
  `new; closest none; proves <outcome>` when the repo has no test that is near it (for example its
  first test). A line whose rest starts with `check:` names a check, not a test.
- Message lines start with `Done-when proof: `. `review.test_run` keeps them in the shown output,
  as it keeps the `RENDERED` lines (`review.py:384`).

### Done-when details

1. The builder's reuse choice (PROOF).
   - `.codex/skills/test-audit/SKILL.md` (and the `.claude` copy), Authoring gate question 3: keep
     its text and add, as its first sentences: `Name the closest existing test; the brief lists the
     tests that name your Scope. Choose reuse when it already proves the outcome, extend when a new
     case or assertion in it can prove it, or new. A new test names the outcome that no existing
     test proves; write "closest none" when no test is near it. Record the choice on the test's
     Proof list line.` This reaches every brief and every review prompt through `design_context`.
   - `brief.md` "When you finish": replace the Proof list paragraph's first two sentences with the
     line form pinned above (numbered lines, the three test name forms, the decision, `check:` only
     for an item that changes only settings, docs or tests) and say what close refuses: an item with
     no test, a named test that is not on the branch, and a named pytest test that did not run,
     failed or was skipped.
   - `review.md` `<!-- proof-list -->` block, after its first paragraph, this text (the test checks
     it, whitespace joined): `$proof_checked For each line, read the
     named test: report a test whose assertions would still pass if the line were false as a P1
     `Test: <the line>`, and a `check:` entry for an item that changes runtime behaviour the same
     way. A new test's line names the closest existing test, or none, and the outcome no existing
     test proves; a missing choice is part of `Gate: proof list`, and a new test whose outcome the
     closest test already proves is a P2 `Follow-up: duplicate test`.`
   - `$proof_checked` says what close checks in this repo, and does not claim a result the reviewer
     cannot yet have, since close's tests can still be running during the review.
     `review.instructions` fills it. Where close or Forge's CI tests job runs the check
     (`test_place` is `local`, or `checks` names `tests`): `When its test run finishes, close
     refuses a Done-when line with no test, a named test that is not on the branch, and a named
     pytest test that did not run, failed or was skipped; that run may still be going while you
     read. For Vitest and Playwright names close checks only that the test is on the branch, so
     judge from the pull request's checks whether they ran and passed.` Otherwise: `Close checks
     only that each Done-when line names a test on the branch. Forge sees no test results here, so
     judge from the pull request's checks whether each named test ran and passed.`
   - `skill.md` Closing section (`:2224-2237`): the same line form and the close refusal, in two
     sentences. Copy over both repo copies of the forge skill.
   - `tests/test_reviews_receive_done_when_proof.py`: its `WORKER_RULE` and `NAMES_RULE` constants
     check the old brief and guide sentences. Change them to the new sentences; nothing else in that
     file changes.
   - Test (new repo): `tests/test_done_when_tests.py::test_1_the_brief_asks_for_the_closest_test_and_the_review_checks_the_choice`.
     A task of an approved story (`start_approved_task`): `forge work` gives a brief
     (`calls(log)[-1]["brief"]`) with the Authoring gate sentences and the brief's line form; after
     `forge close` the review prompt (`env.prompt()`) has the review text.
2. Close checks each Done-when line's test (PROOF).
   - Where:
     - `review.test_run`'s closing path (close's run in a local-test repo, and CI's
       `forge test --change`), after the command's last attempt. Worker runs (`closing=False`) skip
       it. Docs-only changes, sample-data mode and a repo with no test command skip it, because
       `test_run` returns before the run.
     - `prcheck.pr_check` (`forge-pr-check`), with `ran=False` and `head` set to its `--head`
       commit, only when `checks` has no `tests` entry (a repo whose CI runs its own test check).
       This is all such a repo gets.
   - Results come only from a run of the committed code for the current commit and Proof list:
     - On close's local run, `review.test_run` reads `git status --porcelain` in the item's checkout
       once, before it starts the test command (Forge's ignored `.forge/` folder does not show). When
       it lists any file, the check fails with `Done-when proof: The checkout has uncommitted
       changes, so this run did not test the committed code. Commit or remove them, then close
       again.` Files the test run itself creates, such as `__pycache__` in a repo that does not
       ignore it, are never read and never cause a refusal. CI checkouts are clean. The
       `uncommitted-edit` case also covers a clean repo without a `__pycache__` ignore line, where
       close is Ready.
   - Advisory notes from cold read 4, for the builders to weigh (none blocks):
     - Note 36: a shorter reported pytest path can match a longer named one in another app
       (`_ran`'s suffix match); prefer an exact repo-relative match when the hook's root allows it.
     - Note 37: replay copies only `repo.TEST_PATHS` files, so a changed root `conftest.py` stays
       old in the copy; consider copying changed `conftest.py` files too.
     - Note 38: an editable install of the item's checkout can still supply a module the fix adds;
       a pass on old code then wrongly refuses. Watch for it in the `import-error` case.
     - Note 39: `proof_list` shows the worst result across attempts, so a recovered retry can show
       as failed in the pull request; use the same last-attempt rule there.
     - Note 40: the Split out follow-up is not yet a roadmap item; the coordinator records it.
     - `review.passed_record`'s key adds the Proof list text (`review.commit_paragraph(top, base,
       "Proof list:")`), so a proof-only commit runs the tests again and a cached pass is a run of
       the same files and the same list. The cached path restores that run's results file and runs
       `check` on it.
     - `templates/review-tests.py` (and this repo's generated `.forge/review-tests.py`) reuses an
       earlier CI run only when the effective Proof list is the same for both heads: the newest
       `Proof list:` paragraph in each head's history after the base, skipping commits that change
       only paths under `review.BOOKKEEPING` (`.factory/` and `plans/`), the same rule
       `review.commit_paragraph` uses. Existing repos get this on sync.
   - It skips a change whose only files other than Forge's records and plans are `forge.toml` and
     files exactly as `forge sync` writes them (use `repo.generated_files` and `sync.synced`, as
     `githooks._promote` does), and says `Done-when proof: Forge's own settings or generated files
     only; no Done-when test needed.` This keeps the merge switch, upgrade and doctor fixes working
     (their proof lines name no test; `close.generated_fix_proof` does not change).
   - The item: `review.branch_item` of the branch, or of `GITHUB_HEAD_REF` on a detached HEAD
     (`pr_check` already has it). Covered keys: a task's Covers numbers (`review.task`), a fix's one
     `Done when`.
   - The check fails, with one line each:
     - `Done-when proof: Done-when <n> names no test in the Proof list.` (a fix: `The fix's Done-when
       line names no test in the Proof list.`), plus once: `Add a line "<n>: <test>" to the Proof
       list in your last commit message.`
     - `Done-when proof: <name> is not on this branch.` The file is missing, or the case is not in
       it: for pytest, the last `::` part as a whole word, as `proof_list` checks today; for a
       JavaScript title, its last ` > ` part as plain text, since nested suites write each title
       separately. A reused, unchanged test passes this check. This is the only check on a
       Vitest or Playwright name.
     - For pytest names only, from the results of the last attempt of each test (for a file that
       close retried, the lines after the last `fasttest.RETRY_HEADER`), so a test that failed and
       then passed on the retry counts as passed:
       - `Done-when proof: <name> failed in this test run.` (any matching result `failed` or `error`).
       - `Done-when proof: <name> was skipped in this test run. Name the case that proves the line.`
         (any matching result `skipped`, `xfail` or `xpass`, also when other cases passed).
       - `Done-when proof: <name> did not run in this test run.` when no result matches, and only
         when `FORGE_GROUPS` is 1. Forge's pytest hook loads into every pytest the command starts,
         so a command that started no pytest ran none of them.
     - A `check:` line passes with no run.
   - In grouped CI (`FORGE_GROUPS` > 1): the "names no test" and "not on this branch" lines only in
     group 1 (`FORGE_GROUP` 1); "failed" and "skipped" in every group for the names it ran; no "did
     not run".
   - So that a reused pytest test runs: `fasttest.pytest_tests` (`:803`), when it is not a worker
     run, adds the Proof list's pytest names to `named`, which the selection plugin already runs.
   - Failure in close: `test_run` returns non-zero, so close refuses with its `tests_failed` message
     and prints the `Done-when proof:` lines above it. In CI the tests check (or `forge-pr-check`)
     goes red and close's check wait refuses.
   - Shared fixture: `tests/test_close.py::Forge.start` commits its worker change with a Proof list
     (`- Done when: check: <done_when>` for a fix, `- <n>: check: ...` for each covered task item), so
     existing local-test close cases keep passing. Cases that test the refusal write their own.
     Before the PROOF pull request merges, run the close and review test files and
     `tests/test_release_version.py` (guard rule for close and review changes).
   - Test (new repo): `tests/test_done_when_tests.py::test_2_close_refuses_a_done_when_line_without_a_passing_test`,
     local-test pytest repos unless named, parametrized:
     - `pytest-passes`: a fix adds `tests/test_greeting.py` and names
       `tests/test_greeting.py::test_1_greets`; close is Ready, and the pull request's proof list
       says `passed in close's run`.
     - `no-line`, `not-on-branch`, `fails`, `skipped`: close exits 1 with the matching line.
       `skipped` names a file with one passing and one skipped case.
     - `task-item-missing`: a task that covers 1 and 2 maps only 1; close names Done-when 2.
     - `reused-not-selected`: the named test is an unchanged test file that names no changed module;
       close is Ready (the named test joined the selection).
     - `retry-recovered`: the named test times out on the first attempt and passes on close's retry
       (as in `tests/test_close_retries_failed_files.py`); close is Ready.
     - `uncommitted-edit`: an uncommitted edit in the fix's checkout; close exits 1 with the
       "uncommitted changes" line.
     - `proof-only-commit`: after a Ready close, an empty commit whose Proof list names a test that
       fails; the next close runs the tests again and refuses.
     - `javascript-name`: the Proof list names `` `web/a.test.ts::adds` ``; with that file on the
       branch close is Ready without running it, and with the file missing close exits 1 with the
       "not on this branch" line.
     - `ci`: `forge test --change` in the fix's checkout on a detached HEAD with `GITHUB_HEAD_REF`
       set and no Proof list exits 1 with the "names no test" line.
     - `own-ci-check`: a CI-test repo whose `checks` are `["build", "forge-pr-check"]`;
       `forge hook pr-check --base <base> --head <head> --branch fix/<slug>` run from the base
       checkout: a head with no Proof list line exits 1 with the "names no test" line, and a head
       that adds `tests/test_greeting.py` and names it passes the name check, although the base
       checkout has no such file.
     - `review-prompt`: in a repo whose CI runs its own test check, close's review prompt has the
       "Close checks only that each Done-when line names a test on the branch" sentence and not the
       "When its test run finishes" one; in a local-test repo, the other way round.
     - `settings-only`: a fix that changes only `forge.toml`; close does not ask for a test.
3. A commit with an always-true check is refused (LINT).
   - `githooks.pre_commit` (`:122`), after the branch checks and not while `MERGE_HEAD` exists
     (Accepted limits), calls `testlint.check(top)`. It reads staged added or changed files
     (`git diff --cached`, content from `git show :<path>`) that match `repo.TEST_PATHS` and end in
     `.py`, or in `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, `.mts` or `.cts`. This includes the
     starter's `apps/api/test/*.e2e-spec.ts` (`**/test*/**`). It reports only lines this commit adds
     or changes (from `git diff --cached -U0` hunks).
   - Python, with `ast` (a file that does not parse is skipped): `assert` of a true constant (`True`,
     a non-zero number, a non-empty string; `assert False` is fine); `assert A == A` or `assert A is
     A`; `self.assertTrue(<true constant>)`, `self.assertEqual(A, A)`, `self.assertIs(A, A)`. Two
     sides are "the same" when `ast.dump` matches and neither contains a call, since two calls can
     return different values.
   - JavaScript, one line at a time (Accepted limits): `expect(<A>).toBe|toEqual|toStrictEqual(<A>)`
     with the same text `A` that has no `(`; `expect(true).toBeTruthy()`; `assert(true)`;
     `assert.ok(true)`. No multi-line parsing.
   - Refusal, one line per finding, then the fix: `<path>:<line>: this check is always true, so the
     test proves nothing. Assert the outcome the test is for, then commit again.`
   - `brief.md` "Tests first": one sentence that the commit refuses an always-true check and warns
     about a pytest test with no assertion. `skill.md`: the same in the Closing section, copied over
     both copies.
   - Test (new repo): `tests/test_commits_refuse_always_true_checks.py::test_3_a_commit_with_an_always_true_check_is_refused`,
     in a fix's checkout, parametrized: `assert True`, `assert total == total`,
     `self.assertEqual(x, x)` in a pytest file, `expect(total).toBe(total)` in `a.test.ts`,
     `expect(page).toBe(page)` in `a.spec.ts`, `expect(env).toBe(env)` in
     `apps/api/test/env.e2e-spec.ts`: `git commit` exits non-zero and names the file and line.
     `assert make() == make()`, and an old always-true line in a file whose other lines change,
     commit.
4. A test with no assertion (LINT).
   - Python, warning only (5% of Forge's own tests check in a helper): a changed `def test*` whose
     body has no `assert`, no `with pytest.raises` or `pytest.warns`, and no call whose name starts
     with `assert` (this covers `self.assertX` and `mock.assert_called_once`). Message:
     `Warning: <path>:<line> <test name> has no assertion. Add one, or say in the test which helper
     checks the result.` The commit goes ahead.
   - TypeScript: no Forge code. The FORGE-FASTCI-1 starters' Oxlint config turns on
     `vitest/expect-expect`. Oxlint finds test files by name, so Playwright `*.spec.ts` files should
     be included; check this on the starter (Open questions).
   - Tests (new repo): `tests/test_commits_refuse_always_true_checks.py::test_4_a_test_with_no_assertion_gets_a_warning`:
     a pytest test with no assertion commits and prints the warning with its file and line; tests
     that use `pytest.raises` or `mock.assert_called_once()` get no warning. And extend FORGE-FASTCI-1's
     `tests/test_starter_lint_settings.py::test_2_a_module_mock_in_a_test_fails_lint` (which OXLINT
     adds) with the cases `no-assertion-vitest` (a `*.test.ts` with a `test()` that has no `expect`)
     and `no-assertion-playwright` (an `apps/web/e2e/*.spec.ts` the same way): `oxlint` exits
     non-zero and names `expect-expect`.
5. A fix's pytest test must fail on the code before the fix (REPLAY).
   - Fixes only (an item with no `/`), after the run and `check` passed, in close's run and in CI's
     group 1. `proof.replay(top, item, base) -> tuple[bool, list[str]]`.
   - The tests: pytest names on `Done when:` lines whose file the fix added or changed between
     `githooks.fix_base(...)` and HEAD. Vitest and Playwright names get no old-code run (Accepted
     limits). None: no old-code run.
   - The code files: files changed between the fix base and HEAD, without `repo.TEST_PATHS`,
     `review.DOC_EXCLUDES` (records, plans, docs, Markdown, images) and `forge.toml`. None: no
     old-code run.
   - The copy, never the item's checkout:
     - `git worktree add --detach <temp> <fix base>`, with `<temp>` from `tempfile.mkdtemp()`
       outside the repo.
     - Read the fix head first: `head = git rev-parse HEAD` in the item's checkout (in CI, the
       checked-out commit). In the copy, `git checkout <head> -- <test files>` for every test file
       the fix added or changed (the copy's own `HEAD` is the fix base, so `HEAD` there would give
       the old tests), and `git rm -q` for every test file it deleted. Code files stay at the fix
       base, so files the fix deleted are there and files it added are not.
     - The command: `review.close_test(<copy>, base)` built again in the copy and filled with
       `FORGE_GROUPS=1` and `FORGE_GROUP=1` (so a `{group}` shard runs all files), run with
       `PYTHONPATH` starting with `<copy>` and `<copy>/src` (when it exists), so an editable install
       of the checkout cannot supply the new code, and with its own results file. Its exit status
       is not used.
     - In `finally`: `git worktree remove --force <temp>`. Uncommitted work in the item's checkout
       is never read or written.
   - Each named test, from the old-code run's pytest results (last attempt, as in item 2): any
     `failed` is what the fix needs. All `passed` fails the close run with `Done-when proof: <name>
     passed on the code before the fix, so it does not prove the fix. Make it fail there for the
     reported problem.` `error`, `skipped` or no result gives the warning `Done-when proof: <name>
     could not run on the code before the fix (<its first error line, or "it did not run">). The
     review judges it.`
   - A cached pass (same files and Proof list) reuses the saved old-code result lines.
   - `brief.md` (fix section) and the test-audit skill's sentence on bug regression tests: close
     checks this for a fix's pytest tests. `skill.md` Closing section: one sentence. Copy both
     copies of each skill.
   - Test (new repo): `tests/test_fix_tests_fail_before_the_fix.py::test_5_close_refuses_a_fix_whose_test_passes_before_the_fix`,
     local-test pytest repo, parametrized:
     - `fails-then-passes`: the fix changes `app.py` and adds a test of the new behaviour; close is
       Ready.
     - `passes-before`: the fix's new test already passes on the old `app.py`; close exits 1 with the
       "passed on the code before the fix" line.
     - `import-error`: the new test imports a function the fix adds; close is Ready and prints the
       warning.
     - `deletes-a-file`: the fix deletes `old.py` and changes `app.py`; the old-code run sees
       `old.py`, and the checkout still has no `old.py` after close.
     - `test-only`: the fix changes only a test; no old-code run.
     In every case, `git worktree list` shows no extra worktree after close.

### New and existing repos

- **New repos** (`forge init`): the brief, review and guide text, close's Done-when check, the
  old-code run for fixes' pytest tests and the commit check, from the first item.
  FORGE-FASTCI-1's Oxlint config gives the TypeScript no-assertion lint error.
- **Existing repos** (on upgrade to this release):
  - Local-test repos and CI-test repos whose `checks` name `tests`: close's check, the old-code run
    and the commit check, with the release. CI gets them after the upgrade pull request merges,
    because the workflow installs the pinned release; `forge sync` writes the new
    `.forge/review-tests.py`.
  - CI-test repos whose `checks` name their own test check and not `tests`: `forge-pr-check` checks
    that each Done-when line names a test on the branch, and the commit check runs. Close cannot
    check that the test ran or run it on the old code, because Forge sees no test results there.
  - TypeScript apps: Vitest and Playwright names get the "on the branch" check only, as in new
    repos. An app on ESLint gets no lint change from this story (FORGE-FASTCI-1 offers Oxlint).
  - The hooks are shims that call the installed `forge`, so the commit check comes with the release.
    `forge sync` writes the test-audit and forge skill copies.
  - An item open during the upgrade must rewrite its proof list in the numbered form; close's
    message says how. No record changes form, so `tests/test_upgrade_to_installed_release.py` does
    not change.

## Tasks

<!-- One row per task. Covers: the Done-when numbers it delivers, at most three. Scope: the paths
it may change. Before writing each Scope, search the code for the files the task needs. The plan
check refuses two tasks whose Scope paths have the same prefix up to the first wildcard, unless
one waits for the other through After, directly or through another task; it names both tasks.
Paths with a segment named `tests`, `test`, `__tests__` or `spec` do not cause Scope overlaps
and can be shared without an After link. Explicit After links still apply.
When tasks need the same production file, put it in the first task's Scope with the shared names and stubs;
tasks that need them wait for that task through After and then own only their files. Keep a file
that a script can make at build time out of the repo and out of every Scope; when the repo keeps such
a file on purpose, give its change to one part that the others wait for. Tests: the
tests it adds or changes. After: the tasks it waits for. When two tasks share a function, field,
file format or command, the first task pins it: it commits the shared names and stubs plus one
test that crosses both sides, and the tasks that use it list it under After. Split tasks so each
owns its files; shared lines (command table, guide list, registry) go to one task or a small last
wiring task; After only when a task needs another task's code. The
Developer column is optional: the lead fills or changes a GitHub username here, below For the
builders, without another approval. Leave it blank for an unassigned part. Forge next uses
the caller's GitHub login; another developer may start it with a warning. Existing tables
without Developer still work. The moving-parts line stays last: "none", or each new dependency, service, datastore,
queue, background job or abstraction layer, with the Done-when item that needs it. -->

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| PROOF | Each Done-when line's test, checked at close | The builder's reuse choice in the test-audit gate, the brief and the review; the numbered Proof list; close's and CI's check that each covered Done-when line names a test on the branch, and that a named pytest test ran, passed and was not skipped, read only from a run of the committed code for the current commit and list; the name check in `forge-pr-check` for repos with their own CI test check; named pytest tests joined to the selection | 1, 2 | `src/forge/proof.py` (new), `src/forge/review.py` (move `proof_list` out; `passed_record`'s key; `instructions`' `$proof_checked`; call `proof.check` in `test_run`), `src/forge/fasttest.py` (`pytest_tests` only), `src/forge/prcheck.py` (`pr_check` only), `src/forge/close.py` (the three `review.proof_list` calls and the import line only), `src/forge/templates/review-tests.py`, `.forge/review-tests.py`, `src/forge/templates/brief.md`, `src/forge/templates/review.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `.codex/skills/test-audit/SKILL.md`, `.claude/skills/test-audit/SKILL.md`, `tests/test_close.py` (`Forge.start`'s worker commit only), `tests/test_reviews_receive_done_when_proof.py` (`WORKER_RULE` and `NAMES_RULE` only) | `tests/test_done_when_tests.py::test_1_the_brief_asks_for_the_closest_test_and_the_review_checks_the_choice`, `tests/test_done_when_tests.py::test_2_close_refuses_a_done_when_line_without_a_passing_test` (new) | | no | |
| REPLAY | A fix's pytest test fails on the old code | Close's and CI's run of a fix's new or changed pytest Done-when test on the code before the fix, in a temporary worktree: refuse when it passes there, warn when it cannot run there; the item's checkout is never touched | 5 | `src/forge/proof.py`, `src/forge/review.py` (the `replay` call in `test_run` only), `src/forge/templates/brief.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `.codex/skills/test-audit/SKILL.md`, `.claude/skills/test-audit/SKILL.md` | `tests/test_fix_tests_fail_before_the_fix.py::test_5_close_refuses_a_fix_whose_test_passes_before_the_fix` (new) | PROOF | no | |
| LINT | Always-true checks and tests with no assertion | The commit check that refuses always-true checks in pytest tests and one-line always-true checks in Vitest and Playwright tests, and warns about pytest tests with no assertion; the proof that new starters' lint fails a Vitest or Playwright test with no assertion | 3, 4 | `src/forge/testlint.py` (new), `src/forge/githooks.py` (`pre_commit` only), `src/forge/templates/brief.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `src/forge/templates/starter/.oxlintrc.json` and `src/forge/templates/starter-python/.oxlintrc.json` (one e2e override each, only if builder question 1 needs it) | `tests/test_commits_refuse_always_true_checks.py::test_3_a_commit_with_an_always_true_check_is_refused`, `tests/test_commits_refuse_always_true_checks.py::test_4_a_test_with_no_assertion_gets_a_warning` (new); cases `no-assertion-vitest` and `no-assertion-playwright` in `tests/test_starter_lint_settings.py::test_2_a_module_mock_in_a_test_fails_lint` | REPLAY, FORGE-FASTCI-1/OXLINT | no | |

New moving parts: none

## Split out

The owner split this story after cold read 3 (22 Nov 2026). The follow-up is a new item:
**Prove JavaScript Done-when tests ran (Vitest and Playwright reports).** It extends this story's
check to Vitest and Playwright names: the test ran, passed and was not skipped, and a fix's new or
changed JavaScript test fails on the code before the fix. It must handle these cases, from cold
read 3 of this story:

- Note 27: a local run uses the working checkout, so proof must come from the committed code. (This
  story refuses a local close with uncommitted changes; the follow-up keeps that for JavaScript runs.)
- Note 28: a report path is resolved against the Vitest config's `root`, so a report can be written
  outside the folder close reads (the starter's web config sets `root` to `apps/web`).
- Note 29: two extra Vitest runs in one command must not write the same report file.
- Note 30: a Playwright file must never be passed to a Vitest run in a command that has both
  runners.

Also from this story's reads: one test command can run Vitest more than once and overwrite one
JUnit file (the starter's `formats.xml`, which starter smoke's live tests read by name); the Python
starter runs web tests with `--changed`; and an API-only change does not select the starter's
browser tests, though a browser test can reach the API (note 34).

## Notes

- **Order.** PROOF first: it pins `proof.py` and the line form. REPLAY waits for PROOF (same module
  and the same text files). LINT waits for REPLAY only because all three edit `brief.md` and
  `skill.md`; its code shares nothing with them. LINT also waits for FORGE-FASTCI-1/OXLINT, which
  writes the starters' `.oxlintrc.json` and the lint test that LINT extends.
- **Size.** PROOF is about 280 changed lines outside tests and Markdown (about 120 of them are the
  moved `proof_list`). REPLAY is about 90 and LINT about 90.
- **Choice made for the owner to confirm: where the mapping lives.** The plan uses the worker's
  `Proof list:` in place of the story doc's Tests column. It already exists for tasks and fixes,
  close already matches its pytest names to its run, and the builder knows the owning test only
  after the reuse choice. The Tests column maps tests to a task, not to a Done-when line, and is
  fixed at approval. The plan's Done-when details still name the intended test, and the review
  compares the two.
- **Choice made for the owner to confirm: `check:` lines.** The owner's decision says each line
  names its test. The brief's current rule says a settings, docs, deletion or test-only item is
  proven by the check it names. Requiring a test there would push builders to write file-reading
  tests, a junk pattern in the test-audit skill. So a line may say `check:` for those items, and the
  review reports a `check:` line for an item that changes runtime behaviour as P1.
- **Choice made for the owner to confirm: which fixes.** Forge has no bug-fix kind, so the old-code
  run applies to every fix that changes code and names a new or changed pytest test. A fix that
  keeps behaviour the same and changes a test will be refused; such a fix should name its unchanged
  tests.
- **Choice made for the owner to confirm: duplicates do not block.** A new test whose outcome the
  closest test already proves is a P2 follow-up, following the lean-review rule. Make it P1 if
  duplicates must stop the merge.
- **Warn or block, from the evidence.** Always-true checks block: Forge's own suite has none, so a
  block has almost no false alarms. A pytest test with no assertion only warns: 90 of Forge's 1,752
  tests check the result in a helper. In the starters, Oxlint's `expect-expect` is an error through
  FORGE-FASTCI-1; an app can list its helper names in the rule's `assertFunctionNames` setting.
- **Later, not now.** The JavaScript run proof (Split out). Vitest's `expect.requireAssertions`
  setting fails a test that ran no assertion at run time; add it if the lint rule misses assertions
  in callbacks. Multi-line JavaScript assertions in the commit check.
- **Open questions for the owner.**
  1. Repos whose CI runs their own test check get only the name check (Accepted limits). Is that
     enough, or should close run the named tests on the laptop in those repos, which their CI
     choice was meant to avoid?
  2. The old-code run needs a test command that installs its own packages in a fresh copy. Where it
     cannot, every fix gets a warning, not the refusal. Accept this, or let close link the
     checkout's installed Python packages into the copy?
- **Open questions for the builders.**
  1. Does Oxlint's `vitest/expect-expect` check Playwright `*.spec.ts` files? It finds test files by
     name and looks for `test` calls. If not, LINT adds an override for `apps/web/e2e/**` in the
     starters' `.oxlintrc.json` (one line each) and says so.
  2. The Python starter runs pytest with `uv --directory apps/api`, so its node IDs are relative to
     `apps/api`. `proof_list`'s suffix match (`_ran`) should cover this; check it in PROOF.
  3. Measure one Python starter fix's close time after REPLAY; the old-code run installs packages
     and runs the selected pytest tests again. If it adds more than a few minutes, plan a run of
     only the named tests.
- **Changes no setting.** No command, option or `forge.toml` setting; the brief, review and guide
  carry the new steps.
- No client repo is named anywhere in this story's code, tests, texts or commits.
