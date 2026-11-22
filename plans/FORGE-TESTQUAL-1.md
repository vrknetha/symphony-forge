# Make agent-written tests prove real behaviour

3 parts · Risks: none one-way; three accepted limits · New moving parts: none

## What changes for you

- Before a builder adds a test, the builder names the closest test that already exists. The builder then reuses that test, extends it, or adds a new test. A new test says which outcome no existing test proves. The review reports a new test that does not say this. (Source: the owner's decision, 22 Nov 2026)
- Each Done-when line names the test that proves it, in the proof list that the builder writes in the last commit. Close checks that the test is in the change, ran and passed. The review checks that the test's assertion proves the line. A line that changes only settings, docs or tests can name a check in place of a test. (Source: the owner's decision, 22 Nov 2026)
- Git refuses a commit when a test it adds has a check that is always true, such as `assert True` or `expect(x).toBe(x)`, in pytest, Vitest and Playwright tests. (Source: the owner's decision, 22 Nov 2026)
- A new pytest test with no assertion gets a warning at commit, because many good tests check the result in a helper. In a new starter app, lint fails on a Vitest or Playwright test with no assertion. (Source: the owner's decision, 22 Nov 2026)
- For a fix, close also runs the fix's new or changed test on the code before the fix. There the test must fail, and on the new code it must pass. When the test cannot start on the old code, for example because it imports a function that the fix adds, close gives a warning and the review judges the test. (Source: the owner's decision, 22 Nov 2026)
- What each repo gets: a new repo gets all of this at setup. An existing repo gets it when it upgrades Forge and runs sync. In an existing TypeScript app that does not write JUnit test reports to `test-results/`, close cannot see Vitest and Playwright results, so it warns about those tests and does not refuse. An item that is open during the upgrade must write its proof list in the new form at its next close.
- Not in this story: mutation testing (later), a minimum number of assertions, a limit on new tests.

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
2. **Close refuses a task or fix when one of its Done-when lines names no test, or when the named test is not in the change, did not run, failed or was skipped.**
3. **A commit that adds an always-true check to a pytest, Vitest or Playwright test is refused.**
4. **A new pytest test with no assertion gets a warning at commit, and a Vitest or Playwright test with no assertion fails lint in a new starter app.**
5. **Close refuses a fix whose new or changed test passes on the code before the fix, and gives only a warning when that test cannot run on that code.**

## Risks

<!-- Each one-way step: deleting data, a destructive migration, a new vendor. -->

Risks: none one-way. Each part reverts with its pull request. No record changes form.

Accepted limits:
- A fix's tests run twice: once on the new code and once on the code before the fix. This adds
  test time to close (or to CI) for every fix that changes code and a test.
- In CI with more than one test group (Forge's own repo uses six), each group sees only its own
  results, so close cannot prove there that a named test ran. There it checks only that the named
  test passed where it ran. Named pytest tests are added to the test selection so that they run.
- To run the old code, close puts the changed code files back to their old version in the item's
  checkout for one test run and restores them right after. If close is killed in that run, those
  files stay old until `git restore` puts them back; `git status` shows them.

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

Each new test file starts with `STORY = "FORGE-TESTQUAL-1"`, runs the forge command (or git, for
the commit hook) and never imports forge. One test per Done-when item, named `test_<n>_...`.
Close cases use the `env` fixture and helpers of `tests/test_close.py` (`start_fix`,
`start_approved_task`, `close`, `prompt`, `reviews`), `configure` from
`tests/test_testplace_settings.py` for a local-test repo, and `install_claude` and `calls` from
`tests/test_worker.py` for briefs. Real Vitest runs as in `tests/test_close_keeps_full_tests_in_ci.py:133`
(`npm exec --yes --package=vitest@3.2.4 -- vitest run ...`); real Playwright runs the same way with
`@playwright/test@1.64.0` (the starter's pin) and specs that use no browser fixture, so no browser
download is needed. All rules are tested on a new repo only (Review rules).

**What the code does today.**
- The worker's last commit already carries a `Proof list:` paragraph that maps Done-when items to
  tests (`brief.md:816-822`, `skill.md:2224-2237`). `review.proof_list` (`review.py:740-794`)
  writes each named pytest test's result from close's run next to it, from the per-test results
  that Forge's pytest hook writes (`fasttest.py:553-661`, lines `<outcome> <node>`). Other names are
  `not checked`. Nothing refuses a missing or failed entry; only the model review judges it.
- Close runs tests through `review.test_run` (`review.py:387-523`). CI runs the same function
  through `forge test --change` (`prcheck.py:305`, `fasttest.py:340-375`). So `test_run`'s closing
  path is the one place that sees close's run in a local-test repo and CI's run in a CI-test repo.
  In CI the checkout is a detached HEAD, so the branch comes from `GITHUB_HEAD_REF`.
- The starters already write JUnit XML for every runner: `apps/api/vitest.config.ts` and
  `apps/web/vitest.config.ts` (`reporters: ['default', 'junit']` into `test-results/`),
  `apps/web/playwright.config.ts` (`test-results/browser.xml`), and the Python starter's pytest
  (`--junitxml=../../test-results/api.xml`). `test-results/` is in the starters' `.gitignore`.
  So Forge reads Vitest and Playwright results from JUnit files and needs no new reporter.
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
- The FORGE-FASTCI-1 OXLINT part (approved, not yet built) turns on every Oxlint rule group as an
  error with the `vitest` plugin in both starters. `vitest/expect-expect` is in the correctness group
  (https://oxc.rs/docs/guide/usage/linter/rules.html), so new starters get the TypeScript
  no-assertion rule from that part. This story adds no lint setting; LINT only proves it.

**Words this story pins.** PROOF commits these; REPLAY uses them.

- Module `src/forge/proof.py`: `proof_list(top, base, report=None)` (moved, same behaviour, plus
  JUnit names), `entries(top, item, base) -> dict[str, list[str]]` (each covered Done-when key, `"1"`
  or `"Done when"`, to its named tests, or `["check:"]`), and `check(top, item, base, results) ->
  tuple[bool, list[str]]` (passed, message lines). `review.test_run` calls `check` on its closing path.
- Proof list line form, one or more per covered item:
  `- <n>: <test> (<decision>)` for a task (`- 1, 3: ...` covers two items) and
  `- Done when: <test> (<decision>)` for a fix. Regex:
  `^\s*(?:-\s*)?(?P<key>\d+(?:\s*,\s*\d+)*|Done when)\s*:\s*(?P<rest>.*)$`.
  `<test>` is a pytest node ID or file (the existing `TEST_NAME`), or a Vitest or Playwright file
  with an optional title in backticks: `` `apps/web/e2e/sign-in.spec.ts::signs in with a link` ``.
  `<decision>` is `reuse`, `extend <closest test>` or `new; closest <test>; proves <outcome>`.
  A line whose rest starts with `check:` names a check, not a test.
- Message lines start with `Done-when proof: `. `review.test_run` keeps them in the shown output,
  as it keeps the `RENDERED` lines (`review.py:384`).
- JUnit result lines that the check appends to the results file, under `# forge junit results`:
  `<outcome> <repo-relative file>::<title path joined with " > ">`.

### Done-when details

1. The builder's reuse choice (PROOF).
   - `.codex/skills/test-audit/SKILL.md` (and the `.claude` copy), Authoring gate question 3: keep
     its text and add, as its first sentences: `Name the closest existing test; the brief lists the
     tests that name your Scope. Choose reuse when it already proves the outcome, extend when a new
     case or assertion in it can prove it, or new. A new test names the outcome that no existing
     test proves. Record the choice on the test's Proof list line.` This reaches every brief and
     every review prompt through `design_context`.
   - `brief.md` "When you finish": replace the Proof list paragraph's first two sentences with the
     line form pinned above (numbered lines, the three test name forms, the decision, `check:` only
     for an item that changes only settings, docs or tests) and say that close refuses an item with
     no test, or a test that is not in the change, did not run, failed or was skipped.
   - `review.md` `<!-- proof-list -->` block, after its first paragraph, this text (the test checks
     it, whitespace joined): `Close has already refused a Done-when line with no test, and a named
     test that is not in the change, did not run, failed or was skipped. For each line, read the
     named test: report a test whose assertions would still pass if the line were false as a P1
     `Test: <the line>`, and a `check:` entry for an item that changes runtime behaviour the same
     way. A new test's line names the closest existing test and the outcome no existing test proves;
     a missing choice is part of `Gate: proof list`, and a new test whose outcome the closest test
     already proves is a P2 `Follow-up: duplicate test`.` Also change "A pytest name the branch has"
     to name Vitest and Playwright names too.
   - `skill.md` Closing section (`:2224-2237`): the same line form and the close refusal, in two
     sentences. Copy over both repo copies of the forge skill.
   - Test (new repo): `tests/test_done_when_tests.py::test_1_the_brief_asks_for_the_closest_test_and_the_review_checks_the_choice`.
     A task of an approved story (`start_approved_task`): `forge work` gives a brief
     (`calls(log)[-1]["brief"]`) with the Authoring gate sentences and the brief's line form; after
     `forge close` the review prompt (`env.prompt()`) has the review text.
2. Close checks each Done-when line's test (PROOF).
   - Where: `review.test_run`'s closing path (close's run and CI's `forge test --change`), after the
     command's last attempt, and on the cached-pass path against the saved results. Worker runs
     (`closing=False`) skip it. Docs-only changes, sample-data mode and a repo with no test command
     skip it, because `test_run` returns before the run.
   - It skips a change whose only files other than Forge's records and plans are `forge.toml` and
     files exactly as `forge sync` writes them (use `repo.generated_files` and `sync.synced`, as
     `githooks._promote` does), and says `Done-when proof: Forge's own settings or generated files
     only; no Done-when test needed.` This keeps the merge switch, upgrade and doctor fixes working
     (their proof lines name no test; `close.generated_fix_proof` does not change).
   - The item: `review.branch_item` of the branch, or of `GITHUB_HEAD_REF` on a detached HEAD.
     Covered keys: a task's Covers numbers (`review.task`), a fix's one `Done when`.
   - The Proof list: `review.commit_paragraph(top, base, "Proof list:")`.
   - The run fails, with one line each:
     - `Done-when proof: Done-when <n> names no test in the Proof list.` (a fix: `The fix's Done-when
       line names no test in the Proof list.`), plus once: `Add a line "<n>: <test>" to the Proof
       list in your last commit message.`
     - `Done-when proof: <name> is not in this change.` (no such file, or a `::` case that is not a
       whole word in it, as `proof_list` checks today).
     - `Done-when proof: <name> failed in this test run.` (any result `failed` or `error`).
     - `Done-when proof: <name> was skipped in this test run.` (all results `skipped`, `xfail` or `xpass`).
     - `Done-when proof: <name> did not run in this test run.` only when `FORGE_GROUPS` is 1 and the
       runner reported results: the pytest header for a `.py` name, a `# forge junit results` block
       for a JavaScript name.
   - Warning, no failure: `Done-when proof: close could not check <name>: no JUnit report in
     test-results/ named it. The review judges it.` for a JavaScript name when the run wrote no JUnit
     file. A `check:` line passes with no run.
   - In grouped CI (`FORGE_GROUPS` > 1): the "names no test" and "not in this change" lines only in
     group 1 (`FORGE_GROUP` 1); "failed" and "skipped" in every group for the names it ran; no "did
     not run".
   - JUnit: after the command, read `test-results/**/*.xml` under the repo root changed at or after
     the run's start, with `xml.etree.ElementTree`. Per `testcase`: file from `file`, else
     `classname`, with `\` as `/` and `../` collapsed; title from `name` with ` › ` as ` > `;
     outcome `failed` for a `failure` child, `error` for `error`, `skipped` for `skipped`, else
     `passed`. Append the lines to the results file, so a cached pass and `proof_list` see them. A
     JavaScript name matches a case when one file path ends with the other at a `/` and the title
     equals the named title or ends with ` > <named title>`; a file-only name matches all its cases.
   - So that a reused pytest test runs: `fasttest.pytest_tests` (`:803`), when it is not a worker
     run, adds the Proof list's pytest names to `named`, which the selection plugin already runs.
   - Failure in close: `test_run` returns non-zero, so close refuses with its `tests_failed` message
     and prints the `Done-when proof:` lines above it. In CI the tests check goes red and close's
     check wait refuses.
   - Shared fixture: `tests/test_close.py::Forge.start` commits its worker change with a Proof list
     (`- Done when: check: <done_when>` for a fix, `- <n>: check: ...` for each covered task item), so
     existing local-test close cases keep passing. Cases that test the refusal write their own.
     Before the PROOF pull request merges, run the close and review test files and
     `tests/test_release_version.py` (guard rule for close and review changes).
   - Test (new repo): `tests/test_done_when_tests.py::test_2_close_refuses_a_done_when_line_without_a_passing_test`,
     local-test repos, parametrized:
     - `pytest-passes`: a fix adds `tests/test_greeting.py` and names
       `tests/test_greeting.py::test_1_greets`; close is Ready, and the pull request's proof list
       says `passed in close's run`.
     - `no-line`, `not-in-change`, `fails`, `skipped`: close exits 1 with the matching line.
     - `task-item-missing`: a task that covers 1 and 2 maps only 1; close names Done-when 2.
     - `reused-not-selected`: the named test is an unchanged test file that names no changed module;
       close is Ready (the named test joined the selection).
     - `vitest` and `playwright`: real runners whose config writes JUnit to `test-results/`; a
       passing named title is Ready, a title that is not in the file's results gives "did not run".
     - `no-junit`: a Vitest command with no JUnit report; close is Ready and prints the warning.
     - `ci`: `forge test --change` in the fix's checkout on a detached HEAD with `GITHUB_HEAD_REF`
       set and no Proof list exits 1 with the "names no test" line.
     - `settings-only`: a fix that changes only `forge.toml`; close does not ask for a test.
3. A commit with an always-true check is refused (LINT).
   - `githooks.pre_commit` (`:122`), after the branch checks and not while `MERGE_HEAD` exists,
     calls `testlint.check(top)`. It reads staged added or changed files (`git diff --cached`,
     content from `git show :<path>`) that are pytest files (`test_*.py`, `*_test.py`) or JavaScript
     test files (`*.test.*`, `*.spec.*`, with `js`, `jsx`, `ts`, `tsx`, `mjs`, `cjs`, `mts`, `cts`).
     It reports only lines this commit adds or changes (from `git diff --cached -U0` hunks).
   - Python, with `ast` (a file that does not parse is skipped): `assert` of a true constant (`True`,
     a non-zero number, a non-empty string; `assert False` is fine); `assert A == A` or `assert A is
     A`; `self.assertTrue(<true constant>)`, `self.assertEqual(A, A)`, `self.assertIs(A, A)`. Two
     sides are "the same" when `ast.dump` matches and neither contains a call, since two calls can
     return different values.
   - JavaScript, per line: `expect(<A>).toBe|toEqual|toStrictEqual(<A>)` with the same text `A` that
     has no `(`; `expect(true).toBeTruthy()`; `assert(true)`; `assert.ok(true)`.
   - Refusal, one line per finding, then the fix: `<path>:<line>: this check is always true, so the
     test proves nothing. Assert the outcome the test is for, then commit again.`
   - `brief.md` "Tests first": one sentence that the commit refuses an always-true check and warns
     about a pytest test with no assertion. `skill.md`: the same in the Closing section, copied over
     both copies.
   - Test (new repo): `tests/test_commits_refuse_always_true_checks.py::test_3_a_commit_with_an_always_true_check_is_refused`,
     in a fix's checkout, parametrized: `assert True`, `assert total == total`,
     `self.assertEqual(x, x)` in a pytest file, `expect(total).toBe(total)` in `a.test.ts`,
     `expect(page).toBe(page)` in `a.spec.ts`: `git commit` exits non-zero and names the file and
     line. `assert make() == make()`, and an old always-true line in a file whose other lines change,
     commit.
4. A test with no assertion (LINT).
   - Python, warning only (5% of Forge's own tests check in a helper): a changed `def test*` whose
     body has no `assert`, no `with pytest.raises` or `pytest.warns`, and no call whose name starts
     with `assert` (this covers `self.assertX` and `mock.assert_called_once`). Message:
     `Warning: <path>:<line> <test name> has no assertion. Add one, or say in the test which helper
     checks the result.` The commit goes ahead.
   - TypeScript: no Forge code. The FORGE-FASTCI-1 starters' Oxlint config turns on
     `vitest/expect-expect`. Oxlint finds test files by name, so Playwright `*.spec.ts` files are
     included; check this on the starter (Open questions).
   - Tests (new repo): `tests/test_commits_refuse_always_true_checks.py::test_4_a_test_with_no_assertion_gets_a_warning`:
     a pytest test with no assertion commits and prints the warning with its file and line; tests
     that use `pytest.raises` or `mock.assert_called_once()` get no warning. And extend FORGE-FASTCI-1's
     `tests/test_starter_lint_settings.py::test_2_a_module_mock_in_a_test_fails_lint` with the cases
     `no-assertion-vitest` (a `*.test.ts` with a `test()` that has no `expect`) and
     `no-assertion-playwright` (an `apps/web/e2e/*.spec.ts` the same way): `oxlint` exits non-zero
     and names `expect-expect`.
5. A fix's test must fail on the code before the fix (REPLAY).
   - Fixes only (an item with no `/`), after the run and `check` passed, in close's run and in CI's
     group 1. `proof.replay(top, item, base, command)` returns `(passed, lines)`.
   - The tests: names on `Done when:` lines whose file the fix added or changed between
     `githooks.fix_base(...)` and HEAD. None: no old-code run.
   - The code files: files changed between the fix base and HEAD, without `repo.TEST_PATHS`,
     `review.DOC_EXCLUDES` (records, plans, docs, Markdown, images) and `forge.toml`. None: no
     old-code run.
   - The run: `git restore --source=<fix base> --worktree -- <code files>` (this removes files the
     fix added), then the same test command with `FORGE_GROUPS=1` and `FORGE_GROUP=1` and its own
     results file, then, in `finally`, `git restore --source=HEAD --worktree -- <code files>`. Its
     exit status is not used. The review reads a clone, so it does not see these files.
   - Each named test, from the old-code results (pytest hook lines and JUnit lines): any `failed`
     is what the fix needs. All `passed` fails the close run with `Done-when proof: <name> passed on
     the code before the fix, so it does not prove the fix. Make it fail there for the reported
     problem.` `error`, `skipped` or no result gives the warning `Done-when proof: <name> could not
     run on the code before the fix (<its first error line, or "it did not run">). The review judges
     it.`
   - A cached pass reuses the saved old-code result lines.
   - `brief.md` (fix section) and the test-audit skill's sentence on bug regression tests: close
     checks this for fixes. `skill.md` Closing section: one sentence. Copy both copies of each skill.
   - Test (new repo): `tests/test_fix_tests_fail_before_the_fix.py::test_5_close_refuses_a_fix_whose_test_passes_before_the_fix`,
     local-test pytest repo, parametrized:
     - `fails-then-passes`: the fix changes `app.py` and adds a test of the new behaviour; close is
       Ready.
     - `passes-before`: the fix's new test already passes on the old `app.py`; close exits 1 with the
       "passed on the code before the fix" line.
     - `import-error`: the new test imports a function the fix adds; close is Ready and prints the
       warning.
     - `test-only`: the fix changes only a test; no old-code run.
     - `vitest-passes-before`: the same refusal with a real Vitest run and JUnit.
     In every case, after close, `git status --porcelain` in the fix's checkout is empty.

### New and existing repos

- **New repos** (`forge init`): the brief, review and guide text, close's Done-when check, the
  old-code run for fixes and the commit check, from the first item. Starter apps already write
  JUnit reports, so close checks their Vitest and Playwright tests; FORGE-FASTCI-1's Oxlint config
  gives the TypeScript no-assertion lint error.
- **Existing repos** (on upgrade to this release): close's check, the old-code run and the commit
  check come with the release; the hooks are shims that call the installed `forge`. CI-test repos
  get them in CI after the upgrade pull request merges, because the workflow installs the pinned
  release. `forge sync` writes the test-audit and forge skill copies. A TypeScript app without
  JUnit reports in `test-results/` gets warnings, not refusals, for its Vitest and Playwright names;
  the guide says how to add the report line. An app on ESLint gets no lint change from this story
  (FORGE-FASTCI-1 offers Oxlint). An item open during the upgrade must rewrite its proof list in the
  numbered form; close's message says how. No record changes form, so
  `tests/test_upgrade_to_installed_release.py` does not change.

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
| PROOF | Each Done-when line's test, checked at close | The builder's reuse choice in the test-audit gate, the brief and the review; the numbered Proof list; close's and CI's check that each covered Done-when line names a test that is in the change, ran and passed, for pytest and for Vitest and Playwright through JUnit reports; named pytest tests joined to the selection | 1, 2 | `src/forge/proof.py` (new), `src/forge/review.py` (move `proof_list` out; call `proof.check` in `test_run`), `src/forge/fasttest.py` (`pytest_tests` only), `src/forge/close.py` (the three `review.proof_list` calls and the import line only), `src/forge/templates/brief.md`, `src/forge/templates/review.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `.codex/skills/test-audit/SKILL.md`, `.claude/skills/test-audit/SKILL.md`, `tests/test_close.py` (`Forge.start`'s worker commit only) | `tests/test_done_when_tests.py::test_1_the_brief_asks_for_the_closest_test_and_the_review_checks_the_choice`, `tests/test_done_when_tests.py::test_2_close_refuses_a_done_when_line_without_a_passing_test` (new) | | no | |
| REPLAY | A fix's test fails on the old code | Close's and CI's run of a fix's new or changed Done-when test on the code before the fix: refuse when it passes there, warn when it cannot run there, checkout restored after | 5 | `src/forge/proof.py`, `src/forge/review.py` (the `replay` call in `test_run` only), `src/forge/templates/brief.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `.codex/skills/test-audit/SKILL.md`, `.claude/skills/test-audit/SKILL.md` | `tests/test_fix_tests_fail_before_the_fix.py::test_5_close_refuses_a_fix_whose_test_passes_before_the_fix` (new) | PROOF | no | |
| LINT | Always-true checks and tests with no assertion | The commit check that refuses always-true checks in pytest, Vitest and Playwright tests and warns about pytest tests with no assertion; the proof that new starters' lint fails a Vitest or Playwright test with no assertion | 3, 4 | `src/forge/testlint.py` (new), `src/forge/githooks.py` (`pre_commit` only), `src/forge/templates/brief.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md`, `.codex/skills/forge/SKILL.md`, `src/forge/templates/starter/.oxlintrc.json` and `src/forge/templates/starter-python/.oxlintrc.json` (one e2e override each, only if open question 1 needs it) | `tests/test_commits_refuse_always_true_checks.py::test_3_a_commit_with_an_always_true_check_is_refused`, `tests/test_commits_refuse_always_true_checks.py::test_4_a_test_with_no_assertion_gets_a_warning` (new); cases `no-assertion-vitest` and `no-assertion-playwright` in `tests/test_starter_lint_settings.py::test_2_a_module_mock_in_a_test_fails_lint` | REPLAY, FORGE-FASTCI-1/OXLINT | no | |

New moving parts: none

## Notes

- **Order.** PROOF first: it pins `proof.py`, the line form and the results lines. REPLAY waits for
  PROOF (same module and the same text files). LINT waits for REPLAY only because all three edit
  `brief.md` and `skill.md`; its code shares nothing with them. LINT also waits for
  FORGE-FASTCI-1/OXLINT, which writes the starters' `.oxlintrc.json` and the lint test that LINT
  extends.
- **Size.** PROOF is about 300 changed lines outside tests and Markdown (about 120 of them are the
  moved `proof_list`). REPLAY is about 80 and LINT about 90.
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
  run applies to every fix that changes code and names a new or changed test. A fix that keeps
  behaviour the same and changes a test will be refused; such a fix should name its unchanged tests.
- **Choice made for the owner to confirm: duplicates do not block.** A new test whose outcome the
  closest test already proves is a P2 follow-up, following the lean-review rule. Make it P1 if
  duplicates must stop the merge.
- **Warn or block, from the evidence.** Always-true checks block: Forge's own suite has none, so a
  block has almost no false alarms. A pytest test with no assertion only warns: 90 of Forge's 1,752
  tests check the result in a helper. In the starters, Oxlint's `expect-expect` is an error through
  FORGE-FASTCI-1; an app can list its helper names in the rule's `assertFunctionNames` setting.
- **Later, not now.** Vitest's `expect.requireAssertions` setting fails a test that ran no
  assertion at run time; add it if the lint rule misses assertions in callbacks. A focused old-code
  run (only the named tests) for the starter's test script, if the second run is slow.
- **Open questions.**
  1. Does Oxlint's `vitest/expect-expect` check Playwright `*.spec.ts` files? It finds test files by
     name and looks for `test` calls. If not, LINT adds an override for `apps/web/e2e/**` in the
     starters' `.oxlintrc.json` (one line each) and says so.
  2. Vitest's JUnit `classname` for files outside its `root` (the web config includes
     `../../libs/...`) and Playwright's title separator: check both on a starter run before pinning
     the match; the suffix match above is the plan.
  3. The Python starter runs pytest with `uv --directory apps/api`, so its node IDs are relative to
     `apps/api`. `proof_list`'s suffix match (`_ran`) should cover this; check it in PROOF.
  4. The old-code run of a starter fix runs the whole affected project's tests again (stack start
     included). Measure one starter fix's close time after REPLAY; if it is more than a few minutes,
     plan the focused run.
- **Changes no setting.** No command, option or `forge.toml` setting; the brief, review and guide
  carry the new steps.
- No client repo is named anywhere in this story's code, tests, texts or commits.
