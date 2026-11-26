---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-25T17:21:49.600821+00:00
seconds: 312.256
read_hash: aee84b37bb3552b9a2dc6eb1f5b02e0f40f74eea
round: 4
passed: no
doc_seen: aee84b37bb3552b9a2dc6eb1f5b02e0f40f74eea
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 6e210c219c856c53cc3b20e76dc74d0e6a1d6aad
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a1ca23-d19c-7f91-abac-ec3333a0b580
session:
loop_choice: accept
loop_reason: Owner accepted cases 22-25 as known: a wrong guess only changes the quick run; the full run still catches it
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

1. Blocking: Not done: the suggestion can drop a second unit-test step.  
   Raise: Not done  
   Case: normal use - A combined script runs separate Vitest suites for an API and a web app.  
   The plan says to reuse the existing per-kind logic, but [quicktest.py](/src/forge/quicktest.py:91) skips a second runner of the same kind. The [starter package](/src/forge/templates/starter/package.json:14) has two such suites. One would disappear from the suggested command and, if accepted, the pull request check.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - owner decision 11 Nov 2026, "Forge detects, the agent writes it": Forge no longer builds a command from a combined script, so no unit-test step can be dropped; it prints one line and the guide tells the agent to limit every unit-test step (Done-when 1 and 2).

2. Blocking: Not done: expanding an npm script loses effects of the original invocation.  
   Raise: Not done  
   Case: normal use - `npm test` has a `pretest` setup script, or `npm test -- --coverage` forwards a coverage option to its last step.  
   The [plan](/plans/FORGE-SLOWTEST-1.md:65) replaces the invocation with only its script body. npm also runs `pretest` and `posttest`, as its [local documentation](/opt/homebrew/lib/node_modules/npm/docs/content/using-npm/scripts.md:200) shows; the replacement also leaves out arguments supplied on the original invocation. The suggested command can therefore omit setup or coverage checks.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - owner decision 11 Nov 2026, "Forge detects, the agent writes it": the step-rewriting rule is removed; Forge only names the combined script, and the guide tells the agent to keep pre and post scripts, every needed step and the invocation's options (Done-when 1 and 2).

3. Blocking: Not done: the reported combined script still runs browser tests on Windows until a quick setting is accepted.  
   Raise: Not done  
   Case: normal use - A repo has `npm run ci` as its combined test script and has no `fast_test` yet.  
   [review.py](/src/forge/review.py:368) uses the original test setting in that case. The [plan](/plans/FORGE-SLOWTEST-1.md:125) says the Windows skip handles only separate parts and leaves a combined script whole. That contradicts the promised Windows builder run for the case that prompted the story.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - the promise is now exact: a builder's own run on Windows skips separate browser steps only; a test setting that is one combined script still runs whole, browser tests included, until a setting with separate steps is set, and the plan says so to the owner (Done-when 3).

4. Blocking: Not done: the Python picker can start the browser tests that the Windows run just skipped.  
   Raise: Not done  
   Case: normal use - A Python API and a browser suite use `test = "pytest && npm run test:e2e"` and a quick setting containing `forge test --pytest {base} && npm run test:e2e`.  
   The outer run can remove the browser part, but [pytest_tests](/src/forge/fasttest.py:697) reads the full test setting again. It drops Node parts only when it also finds Vitest or Jest. The [planned change](/plans/FORGE-SLOWTEST-1.md:129) adds `browser` to that same conditional list, so this Python-and-browser command still runs the browser suite.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - one skip helper runs on all three paths of a builder's own run on Windows: the bare forge test command, the pytest picker's reread test setting, and close_tests; test_3 covers the Python-and-browser cases.

5. Blocking: Unproven: item 3: the generated Node wrapper survives the suggestion.  
   Raise: Test  
   Case: normal use - A new repo accepts the suggestion generated from Forge’s default Node test setting.  
   [quicktest.py](/src/forge/quicktest.py:44) unwraps only the exact original setting. An expanded suggestion has a different wrapped command, so its last script name retains the closing parenthesis when split. The [Windows test](/plans/FORGE-SLOWTEST-1.md:142) uses an unwrapped setting and can pass while the browser step in the generated suggestion is not recognized.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - owner decision 11 Nov 2026, "Forge detects, the agent writes it": Forge builds no new suggestion, so nothing new is wrapped; the Windows skip leaves the generated Node wrapper command unchanged.

6. Blocking: Not done: unrelated scheduled workflows would appear as failed nightly tests.  
   Raise: Not done  
   Case: normal use - A repo has a failed weekly maintenance workflow and no nightly test run.  
   [failed_schedules](/src/forge/board_facts.py:406) reads scheduled runs across all workflows. The [plan](/plans/FORGE-SLOWTEST-1.md:162) adds each failure as a “nightly” row, so this repo would show an entry despite the promise that a repo with no nightly run shows none.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - only the full test run Forge knows (full_suite_workflow, else forge.yml in a CI-test repo) gives a Needs you entry and the Needs you prefix; other scheduled workflows keep today's next lines and never show on the board (Done-when 4, test_4).

7. Blocking: Not done: a failed-run entry can disappear before another run passes.  
   Raise: Not done  
   Case: normal use - The next nightly run starts while the previous one is still failed.  
   [failed_schedules](/src/forge/board_facts.py:429) picks the newest run before checking its conclusion. Once its cache refreshes, an in-progress or cancelled run hides the earlier failure. The [plan](/plans/FORGE-SLOWTEST-1.md:191) tests a passing run but not this state.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - per workflow, the newest run whose conclusion is success or failure decides; an in-progress, cancelled or skipped run never removes the entry (Done-when 6, test_6).

8. Blocking: Unproven: item 4: a merged fix can keep hiding later failures.  
   Raise: Test  
   Case: normal use - A fix for a failed run merges, then the same workflow fails again.  
   The [plan](/plans/FORGE-SLOWTEST-1.md:162) identifies claiming fixes through `best`. The board determines that a fix is merged separately when it [derives its row](/src/forge/board.py:381); the stored state in `best` can still say `ready`. The proposed test stops after starting a fix, so it would pass if that old fix suppressed every later failure.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - a fix never hides the entry; a fix whose board state is not done only changes the row's words, and test_6 covers a merged fix followed by a new failure (Done-when 6).

9. Blocking: Unproven: item 4: the board link is never exercised.  
   Raise: Test  
   Case: normal use - A person clicks a failed-run row on the board.  
   The [planned test](/plans/FORGE-SLOWTEST-1.md:183) checks JSON and next-step text only. The existing [row handler](/src/forge/board_app/now.js:127) opens an item drawer, so those assertions can all pass while clicking the new row never opens the run on GitHub.  
   Gain 3, Work 2, Harm 3
   Disposition: cut - Done-when 5 and test_5 in the real-Chrome board harness of tests/test_board_now_screen.py click the row and check that a new page opens at the run's url; the board JSON entry carries url (test_4).

10. Blocking: Gate: the three new tests use the same story test number.  
    Raise: Gate  
    Case: normal use - Both parts add the tests named in their task rows.  
    The [plan](/plans/FORGE-SLOWTEST-1.md:217) names all three new tests `test_1`. [test_rules.py](/tests/test_rules.py:26) requires test numbers to be unique across a story, so the required repository check would fail.  
    Gain 4, Work 1, Harm 2
    Disposition: cut - each Done-when has its own test number, test_1 to test_6, unique across the story's files.

## Round 2

11. Blocking: Not done: the suggestion moves post-test steps ahead of the tests.  
    Raise: Not done  
    Case: normal use - A repo runs `npm run ci && npm run report`, where the report reads results produced by the combined `ci` script.  
    The amended [plan](/plans/FORGE-SLOWTEST-1.md:74) puts the other parts of the test setting first, followed by the expanded script. The suggested command therefore runs the report before the tests. Once accepted, that command is also used by the pull request check.  
    Gain 5, Work 2, Harm 3
    Disposition: cut - owner decision 11 Nov 2026, "Forge detects, the agent writes it": Forge builds no suggestion from a combined script, so it cannot reorder steps; the guide tells the agent to keep every step in the script's order, including steps after the tests.

12. Advisory: Not done: frequent scheduled jobs can crowd out the failed full run.  
    Raise: Not done  
    Case: normal use - A repo has a nightly full test and another scheduled job every five minutes.  
    [failed_schedules](/src/forge/board_facts.py:406) reads only the newest 100 scheduled runs across all workflows. After about eight and a half hours, the other job can push the failed nightly run out of that list. The [amended plan](/plans/FORGE-SLOWTEST-1.md:184) filters the returned runs but does not change that limit, so the row can disappear without a passing full run.  
    Gain 3, Work 2, Harm 3
    Disposition: cut - the row is found by the full-run mark: the request for the full run's own workflow runs drops its event filter, so other frequent jobs cannot push its newest result out (detail 4).

13. Advisory: Not done: a separate browser-test script can escape the Windows skip.  
    Raise: Not done  
    Case: normal use - A test setting has a separate `npm run test:browser` step whose package script runs `node scripts/test-browser.mjs`.  
    The [planned classifier](/plans/FORGE-SLOWTEST-1.md:123) looks for `playwright` or `cypress` in the command or its one-level script body. Forge’s [Python starter package](/src/forge/templates/starter-python/package.json:16) uses that Node script form, and the [script](/src/forge/templates/starter-python/scripts/test-browser.mjs:28) invokes Playwright internally. The step would still run on Windows despite the promise to skip separate browser-test steps.  
    Gain 3, Work 3, Harm 3
    Disposition: cut - the plan states the limit: a step that reaches Playwright through another file, such as the Python starter's browser script, is not recognised and still runs, and the brief says so (detail 3).

14. Advisory: Not done: the board cuts off the words saying a fix is in progress.  
    Raise: Not done  
    Case: normal use - A fix is started for a failed run on `main`.  
    The [planned title](/plans/FORGE-SLOWTEST-1.md:236) puts “a fix is in progress” after the failure description. The existing [row style](/src/forge/board_app/now.css:103) limits the card to 300 pixels and cuts its title to one line. The progress words fall beyond the visible width, while clicking the row opens GitHub rather than its full board text.  
    Gain 3, Work 1, Harm 3
    Disposition: cut - the fix-in-progress words go in the row's short label place (Fix in progress in place of Full test run), and the title stays, so they fit the existing one-line row (detail 6).

15. Advisory: Not done: some workflow names prevent the row from identifying its fix.  
    Raise: Not done  
    Case: normal use - A repo names its full workflow `nightly@2am.yml` and starts the suggested fix.  
    [nextstep.py](/src/forge/nextstep.py:436) removes `@` when constructing the fix’s reason, while the [amended plan](/plans/FORGE-SLOWTEST-1.md:236) matches that reason against the original filename. The repo already tests this supported [workflow name](/tests/test_next_step_argument_quoting.py:23); its row would not say the fix is in progress.  
    Gain 3, Work 2, Harm 3
    Disposition: cut - the row matches the fix with the same cleaned file key that claim uses, built with nextstep's clean, so a name such as nightly@2am.yml still matches (detail 6).

16. Advisory: Unproven: the existing schedule cache lacks the new board fields after upgrade.  
    Raise: Test  
    Case: normal use - An earlier-adopted repo runs `forge next` during a failed nightly run, then upgrades within ten minutes.  
    The existing [cache](/src/forge/board_facts.py:178) can return the old failure record without `full_run`, the run URL or its date. The [plan](/plans/FORGE-SLOWTEST-1.md:191) accounts for the per-attempt cache but not this outer cache, and its upgrade case does not exercise a populated old cache.  
    Gain 3, Work 2, Harm 2
    Disposition: cut - a schedule cache from an earlier release whose entries lack full_run is treated as stale and read again (detail 4).

## Round 3

17. Blocking: Not done: a non-full run can clear a failed full test run.  
    Raise: Not done  
    Case: normal use - A configured workflow runs full tests nightly and a shorter check on pushes to main.  
    The [plan](/plans/FORGE-SLOWTEST-1.md:170) removes the event filter and treats runs from that workflow as full runs. A successful push check can therefore remove the failed-nightly row even though no later full test passed. Forge’s [generated workflow](/src/forge/prcheck.py:293) also shows that a full-suite job can be limited to specific events.  
    Gain 5, Work 2, Harm 3
   Disposition: cut - the full run's own request keeps its event filters: today's manual request stays and one `event=schedule` request is added, so push and pull request runs are never read and cannot clear a failure (detail 4).

18. Advisory: Not done: skipping a browser script can also skip its setup.  
    Raise: Not done  
    Case: normal use - `npm run test:e2e` runs Playwright, its `pretest:e2e` script builds the app, and a later API-test step needs that build.  
    The [browser classifier](/plans/FORGE-SLOWTEST-1.md:105) checks the script body but not its lifecycle scripts. On Windows it removes the whole invocation, including the [npm pre-script](/opt/homebrew/lib/node_modules/npm/docs/content/using-npm/scripts.md:16), so the later API tests can fail.  
    Gain 3, Work 2, Harm 3
   Disposition: cut - a script with a `pre<script>` or `post<script>` script is not classified as a browser part and still runs, setup included; a test case covers it (detail 3).

19. Advisory: Plan gap: the workflow request change breaks an existing test outside the task’s scope.  
    Raise: Plan gap  
    Case: normal use - The full-run test suite runs after NIGHTLY is built.  
    The [plan](/plans/FORGE-SLOWTEST-1.md:174) removes `event=workflow_dispatch`, but [test_testplace_fullrun.py](/tests/test_testplace_fullrun.py:431) requires that field on a workflow request. The test is absent from [NIGHTLY’s scope](/plans/FORGE-SLOWTEST-1.md:265).  
    Gain 4, Work 1, Harm 2
   Disposition: cut - the `event=workflow_dispatch` request stays, so `test_testplace_fullrun.py` passes unchanged and NIGHTLY's scope needs no change (detail 4).

20. Advisory: Not done: a quoted test pattern is mistaken for a combined script.  
    Raise: Not done  
    Case: normal use - A package script runs `jest --testNamePattern="login|signup"`.  
    The [new rule](/plans/FORGE-SLOWTEST-1.md:60) treats any `|` in the script body as a combined command. This pipe is inside a quoted pattern; [quicktest.py](/src/forge/quicktest.py:59) currently recognizes the single Jest command and suggests a quick test. The planned rule removes that existing suggestion.  
    Gain 3, Work 2, Harm 3
   Disposition: cut - the combined-script rule ignores text inside quotes, so `jest --testNamePattern="login|signup"` keeps today's suggestion; a test case covers it (details 1 and 3). The read file names a quoted `|` as the separator; the task text said `/`, and `|` is what the rule uses.

21. Advisory: Functional: a browser-only setting is reported as missing.  
    Raise: Functional  
    Case: normal use - On Windows, a repo’s test setting is only `npm run test:e2e`, which runs Playwright.  
    The [planned skip](/plans/FORGE-SLOWTEST-1.md:113) leaves an empty command. [review.test_run](/src/forge/review.py:402) then says `forge.toml` names no test command, although it does.  
    Gain 2, Work 1, Harm 1
   Disposition: keep - below the bar (live with)

## Round 4

22. Advisory: Not done: a workspace test can lose its unit tests on Windows.  
    Raise: Not done  
    Case: normal use - `npm run test --workspace=web` runs a workspace script containing Vitest and Playwright, while the root script named `test` runs only Playwright.  
    [quicktest.py](/src/forge/quicktest.py:41) reads the root `package.json`, but npm runs the [workspace’s script](/opt/homebrew/lib/node_modules/npm/docs/content/using-npm/workspaces.md:151). The [planned classifier](/plans/FORGE-SLOWTEST-1.md:110) can therefore remove the whole workspace step, including Vitest.  
    Gain 3, Work 2, Harm 3
   Disposition: keep - Owner accepted cases 22-25 as known: a wrong guess only changes the quick run; the full run still catches it

23. Advisory: Not done: a lint step can be mistaken for browser tests.  
    Raise: Not done  
    Case: normal use - A repo runs `npm run lint:browser`, whose script is `eslint playwright` to lint files in its `playwright` directory.  
    The [planned rule](/plans/FORGE-SLOWTEST-1.md:110) classifies a script that names `playwright` as a browser part. It would skip this lint step on Windows, although the step runs no browser tests.  
    Gain 3, Work 2, Harm 3
   Disposition: keep - Owner accepted cases 22-25 as known: a wrong guess only changes the quick run; the full run still catches it

24. Advisory: Not done: a Corepack command does not trigger combined-script detection.  
    Raise: Not done  
    Case: normal use - An adopted Node repo sets `test = "corepack pnpm test"` and has no `fast_test`.  
    Forge’s [testing guide](/src/forge/templates/conventions/testing.md:14) uses Corepack with a combined pnpm test script. The [detection rule](/plans/FORGE-SLOWTEST-1.md:60) accepts calls beginning with the package manager, while [quicktest.py](/src/forge/quicktest.py:56) does not recognize the `corepack` prefix. Forge prints no combined-script line.  
    Gain 3, Work 2, Harm 3
   Disposition: keep - Owner accepted cases 22-25 as known: a wrong guess only changes the quick run; the full run still catches it

25. Advisory: Unproven: item 3: directly invoked browser commands.  
    Raise: Test  
    Case: normal use - A Windows repo runs `playwright test` directly as a separate step, with Playwright available on its path.  
    [test_parts](/src/forge/quicktest.py:66) currently recognizes Node parts by package-manager prefixes. The [planned test](/plans/FORGE-SLOWTEST-1.md:151) uses only `npm run test:e2e`, so it can pass while the direct step still runs.  
    Gain 3, Work 2, Harm 3

Tests were not run. The story-state file was already modified when this read began; it did not change during the read.
   Disposition: keep - Owner accepted cases 22-25 as known: a wrong guess only changes the quick run; the full run still catches it
