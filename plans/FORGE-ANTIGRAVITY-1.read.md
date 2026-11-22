---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-22T12:48:00.909318+00:00
seconds: 777.217
read_hash: d14778be4180c489dac112e4c062c7f03b992716
round: 4
passed: no
doc_seen: d14778be4180c489dac112e4c062c7f03b992716
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 96718861630258e7861fc785a3ec418d30bb3808
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a202f2-fbec-7e52-97bc-9060b98f67be
session:
loop_choice: accept
loop_reason: Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval
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

1. Blocking: A review can run commands supplied by the change it is reviewing.
   Raise: Security
   Case: normal use - A change includes an Antigravity startup hook, and `forge close` reviews that change.
   [review.py](/src/forge/review.py:885) clones the branch into the review tree, and the [plan](/plans/FORGE-ANTIGRAVITY-1.md:130) starts Antigravity there. A [reported Antigravity 1.5.2 defect](https://github.com/google-antigravity/antigravity-cli/issues/1449) shows that its ACP mode runs workspace hooks without a trust check or permission request. Version 1.5.2 is within the plan’s supported range.
   Adds work: isolate repository-provided customizations during reviews; F 2 x H 3 = 6; 2 x C = 6
   Gain 5, Work 3, Harm 5
   Disposition: cut: Forge runs its own Antigravity review in the throwaway review clone after isolate removes the change's .agents, .agent and .gemini folders and its origin remote, and writes only Forge's guard with an absolute forge command; the REVIEW test plants three markers that must never run.

2. Blocking: Read mode does not ensure that a cold reader leaves files unchanged.
   Raise: Security
   Case: normal use - A developer has allowed workspace edits or uses Antigravity’s automatic mode, then starts a cold read.
   The [plan](/plans/FORGE-ANTIGRAVITY-1.md:109) rejects edits only when Antigravity asks permission; it does not set or enforce a read-only policy. [Google’s permissions documentation](https://antigravity.google/docs/permissions) says allowed actions and automatic edits can proceed without such a request. [story.py](/src/forge/story.py:369) detects some changes after the read, but does not undo them. The planned stub always asks for edit permission, so it cannot expose this case.
   Adds work: enforce read-only execution for readers; F 3 x H 3 = 9; 2 x C = 6
   Gain 5, Work 3, Harm 5
   Disposition: cut: cold reads run in a throwaway checkout removed after the read; test 3 proves a reader's write never reaches the story checkout.

3. Blocking: Not done: item 4: A locally selected Antigravity worker starts without Forge’s command guard.
   Raise: Security
   Case: normal use - A developer selects `workers = "antigravity"` in `forge.local.toml`.
   [repo.py](/src/forge/repo.py:667) applies that setting to work, but [sync.py](/src/forge/sync.py:434) renders committed files from shared settings only. The [plan](/plans/FORGE-ANTIGRAVITY-1.md:100) therefore writes no guard for this selection, yet starts the worker with permission checks skipped.
   Gain 5, Work 2, Harm 5
   Disposition: cut: turn refuses a build when the checkout's .agents/hooks.json lacks Forge's guard; test 4 covers a forge.local.toml-only choice.

4. Blocking: Not done: item 4: The planned guard can be skipped on supported Windows versions.
   Raise: Security
   Case: normal use - A Windows developer uses Antigravity 1.5.0 through 1.5.7.
   The [plan](/plans/FORGE-ANTIGRAVITY-1.md:101) uses the quoted shell command from [sync.py](/src/forge/sync.py:65). [Google’s 1.5.8 changelog](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md) says Windows could silently skip hook commands containing double quotes. The planned test invokes the command with `sh -c`, so it does not exercise Antigravity’s Windows hook runner.
   Gain 5, Work 3, Harm 5
   Disposition: cut: the version floor is now 1.5.12, after the 1.5.8 Windows hook fix; the live test runs once on Windows.

5. Blocking: Sync overwrites an existing Antigravity hook or skills manifest.
   Raise: Data loss
   Case: normal use - A repo already using Antigravity has its own hooks or extra skill folders before enabling it in Forge.
   The [plan](/plans/FORGE-ANTIGRAVITY-1.md:100) specifies complete replacement contents for both files. [sync.py](/src/forge/sync.py:600) writes rendered contents over existing files; its existing host-hook renderer instead preserves other entries.
   Adds work: preserve existing Antigravity configuration when syncing; F 2 x H 3 = 6; 2 x C = 4
   Gain 5, Work 2, Harm 5
   Disposition: cut: sync sets only Forge's key and entry and keeps other hooks and skill entries; test 4 covers it.

6. Blocking: Not done: item 4: Stopping an Antigravity review does not track its agent process.
   Raise: Functional
   Case: normal use - A person stops a review while Antigravity or one of its background tasks is still running.
   The [plan](/plans/FORGE-ANTIGRAVITY-1.md:108) gives each Antigravity process its own process group, including the one launched inside the review helper. [autoreview.py](/src/forge/autoreview.py:166) registers the helper, while [machine.py](/src/forge/machine.py:650) stops the registered group. The nested group is not registered with the parent. [Google’s changelog](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md) also records background tasks surviving session closure before 1.5.10.
   Gain 4, Work 2, Harm 3
   Disposition: cut: the Antigravity review runs in Forge's own process under agent_process inside the review's agent_slot, with no helper in between; the 1.5.12 floor includes the 1.5.10 background-task fix.

7. Blocking: The board work promised to the owner has no implementation or test.
   Raise: Plan gap
   Case: normal use - A person looks at an Antigravity run on the board or in the pane.
   The [plan](/plans/FORGE-ANTIGRAVITY-1.md:12) promises its family, model, effort and token use, but neither task owns the board or pane. [board.py](/src/forge/board.py:454) does not expose token use there, and the [pane](/src/forge/mod/hooks/register.ts:21) recognizes only Claude and GPT model names.
   Adds work: display the promised run details; F 3 x H 2 = 6; 2 x C = 6
   Gain 5, Work 4, Harm 3
   Disposition: cut: the board and pane promise is removed from What changes for you.

8. Blocking: Not done: item 1: The default model cannot run on common personal accounts.
   Raise: Functional
   Case: normal use - A person signs in with a Free or Plus Google account and enables Antigravity without model overrides.
   The [plan](/plans/FORGE-ANTIGRAVITY-1.md:9) promises that sign-in works with Gemini 4 Neon as the default. [Google’s model list](https://antigravity.google/docs/models) says Neon is unavailable on Free and Plus. The owner-facing text does not say those users must choose another model, and the stub always offers Neon.
   Gain 3, Work 2, Harm 3
   Disposition: cut: the default model is the plan's default (model = "default"); the Neon plan limit is stated; test 1 covers a plan without Neon.

9. Blocking: The review selector has no builder or item at its early call site.
   Raise: Plan gap
   Case: normal use - `forge close` checks the selected reviewer before changing state.
   [close.py](/src/forge/close.py:200) calls `require_engine(cfg)`. The [plan](/plans/FORGE-ANTIGRAVITY-1.md:129) makes that function use `state["worker"]` and an item name, neither of which its interface receives; REVIEW’s Scope also excludes `close.py`.
   Gain 4, Work 2, Harm 2
   Disposition: cut: require_engine(cfg, state, item) at close.py:202 and review.py:864, with close.py in READS's Scope.

10. Blocking: Antigravity reviews are attributed to the helper’s Claude model.
    Raise: Not done
    Case: normal use - A repo runs a code review on Antigravity.
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:130) invokes the helper as Claude without model or effort arguments. The pinned helper prints its Claude default, and [autoreview.py](/src/forge/autoreview.py:188) records that printed model as the review’s model. The planned test checks family and tokens, but not the recorded model and effort.
    Gain 3, Work 2, Harm 3
   Disposition: cut: the Antigravity review never goes through the helper; turn records the model the session reports, and the REVIEW test checks it.

11. Blocking: Not done: item 6: Setup cannot say whether Antigravity is ready.
    Raise: Not done
    Case: normal use - Antigravity is installed but the person has not signed in.
    The [setup rule](/plans/FORGE-ANTIGRAVITY-1.md:136) deliberately checks installation only and prints the same line for signed-in and signed-out users. It therefore cannot provide the readiness result promised by item 6.
    Gain 3, Work 2, Harm 3
   Disposition: cut: item 6 now promises only that a supported Antigravity is installed; doctor checks the sign-in.

12. Blocking: Not done: item 5: Doctor treats an unknown sign-in result like a successful check.
    Raise: Not done
    Case: normal use - Antigravity is installed, but its sign-in check encounters a temporary service or protocol error.
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:134) returns `None` for that error and reports only a definite signed-out result. With no other problems, [doctor.py](/src/forge/doctor.py:519) can then say everything checks out even though sign-in was not established.
    Gain 3, Work 2, Harm 3
   Disposition: cut: an unknown sign-in result is a problem line; test 5 covers it.

13. Blocking: The planned refusal tests conflict with when Forge commits the worker state.
    Raise: Plan gap
    Case: normal use - The account is signed out or the configured model is unavailable.
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:117) requires both refusals to leave no state commit, but checks them inside the Antigravity turn. [worker.py](/src/forge/worker.py:313) commits the working state before starting that turn.
    Adds work: keep these refusals before the state commit; F 2 x H 2 = 4; 2 x C = 4
    Gain 4, Work 2, Harm 2
   Disposition: cut: install and version refuse before the state commit; sign-in and model refusals come after it, as Claude's turn failures do, and the test checks a failed round.

14. Blocking: Read and review failures give the next command for a worker.
    Raise: Functional
    Case: normal use - A signed-out account starts an Antigravity cold read or review.
    The shared [turn refusals](/plans/FORGE-ANTIGRAVITY-1.md:111) direct every caller to `forge work`, although cold reads use `forge read` and reviews use `forge close`. The reused [no-turn refusal](/src/forge/worker.py:84) also names Claude.
    Gain 3, Work 2, Harm 3
   Disposition: cut: turn takes the retry command (forge work or forge read), and Antigravity's own no-turn text names Antigravity.

15. Blocking: An Antigravity question can be discarded instead of reaching the coordinator.
    Raise: Functional
    Case: normal use - A worker asks a necessary question through Antigravity’s question tool.
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:109) cancels that request without recording its contents. [worker.py](/src/forge/worker.py:447) records only a trailing `Question:` in the final text, so the question is lost if the agent does not repeat it there.
    Adds work: carry the question into Forge’s existing question flow; F 2 x H 2 = 4; 2 x C = 4
    Gain 3, Work 2, Harm 3
   Disposition: cut: an interaction question is appended as a Question: block, so the existing question flow carries it; test 1 covers it.

16. Blocking: Unproven: item 1: An Antigravity worker builds a fix.
    Raise: Test
    Case: normal use - A repo sends an ordinary fix to Antigravity.
    The [planned build test](/plans/FORGE-ANTIGRAVITY-1.md:117) starts only a task. [worker.py](/src/forge/worker.py:211) chooses a separate work kind for fixes, so that test can pass while fixes route incorrectly or use the wrong model settings.
    Gain 3, Work 2, Harm 3
   Disposition: cut: test 1 adds a fix case with models.lite.antigravity.

17. Blocking: Split: BUILD → the agent runtime and the guard/skills integration.
    Raise: Plan gap
    Case: normal use - One builder implements BUILD within its assigned Scope.
    The [task estimate](/plans/FORGE-ANTIGRAVITY-1.md:172) is already about 340 production lines, excluding the new protocol stub, command-level tests, live tests and three guide copies. Its Scope therefore suggests well over the approximately 400 changed-line task limit.
    Gain 4, Work 2, Harm 2
   Disposition: cut: BUILD is split into RUNTIME (1, 2) and GUARD (4); READS covers 3, 5, 6.

## Round 2

18. Blocking: Antigravity reviews send credential files that the existing reviewer excludes.
    Raise: Data loss  
    Case: normal use - A change accidentally includes a tracked `.env.production` or private key.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:117) sends the raw diff to Antigravity. The pinned [review helper](/Users/ravikiranvemula/.codex/skills/autoreview/scripts/autoreview:2383) removes sensitive paths from that diff; [Forge’s generated-file filter](/src/forge/autoreview.py:59) does not replace that protection.  
    Adds work: preserve the existing sensitive-file exclusion; F 2 x H 3 = 6; 2 x C = 4  
    Gain 5, Work 3, Harm 5

   Disposition: cut: the evidence comes from the helper's own validate_review_patch, and isolate removes the helper's tracked_sensitive_paths from the copy; the review test has a .env.production case.

19. Blocking: Not done: item 3: Git can run a change’s hook before review isolation.
    Raise: Security  
    Case: normal use - A developer has a relative `core.hooksPath` in their Git configuration, and the change adds a `post-checkout` hook there.  
    [review.py](/src/forge/review.py:891) clones the branch before the planned isolation runs. Git runs `post-checkout` after a clone and resolves a relative hooks path in the checkout, so the change’s script can execute with the developer’s permissions. [Git hooks](https://git-scm.com/docs/githooks), [Git configuration](https://git-scm.com/docs/git-config).  
    Gain 5, Work 2, Harm 5

   Disposition: cut: clean_git ignores system and user git configuration and sets an empty core.hooksPath for the clone and in the copy's own config; the review test has a post-checkout case.

20. Blocking: Not done: item 3: Preparing the review diff can execute a script from the change.
    Raise: Security  
    Case: normal use - A developer’s Git configuration names a repository script as a text-conversion driver, and the change edits that script and a matching file.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:117) runs `git diff --no-ext-diff` before isolation. Git still runs text-conversion drivers unless `--no-textconv` is given; the pinned [review helper](/Users/ravikiranvemula/.codex/skills/autoreview/scripts/autoreview:52) uses that flag. [Git diff documentation](https://git-scm.com/docs/git-diff).  
    Gain 5, Work 2, Harm 5

   Disposition: cut: no user git configuration, plus the helper's SAFE_GIT_CONFIG_ARGS and SAFE_DIFF_FLAGS (with --no-textconv); the review test has a textconv case.

21. Blocking: Not done: item 3: A reviewed `AGENTS.md` becomes instructions for its reviewer.
    Raise: Security  
    Case: normal use - A change edits `AGENTS.md` to tell the reviewer to suppress a finding.  
    The [isolation rule](/plans/FORGE-ANTIGRAVITY-1.md:113) leaves that file in the review checkout as “text.” [Google’s rules documentation](https://antigravity.google/docs/rules) says Antigravity automatically loads it as an always-active rule. The existing [review helper](/Users/ravikiranvemula/.codex/skills/autoreview/scripts/autoreview:3897) instead tells reviewers that source files are evidence, not instructions.  
    Gain 5, Work 3, Harm 5

   Disposition: cut: isolate removes every AGENTS.md, GEMINI.md and CLAUDE.md, their diff stays in the evidence, and the prompt carries the helper's evidence line; the review test has an AGENTS.md case.

22. Blocking: Not done: item 3: A reader can change the original checkout from its throwaway copy.
    Raise: Security  
    Case: normal use - A developer has an Antigravity allow rule for writing files outside the active workspace.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:113) changes the working directory and removes the copy’s remote, but does not restrict writes to that directory. [Google’s permissions](https://antigravity.google/docs/permissions?tab=cli) permit rules such as `write_file(*)` without a request. The [snapshot check](/src/forge/story.py:369) does not undo a write; an ignored file can escape its snapshot altogether. The planned test writes only inside the copy.  
    Gain 5, Work 4, Harm 5

   Disposition: cut: reads and reviews run on Forge's read profile (--gemini-dir), whose Antigravity deny rules refuse every write and command, with none of the user's allow rules; the test has an outside-write case.

23. Blocking: Not done: item 3: A later cold read opens the old committed plan.
    Raise: Functional  
    Case: normal use - The coordinator amends a plan after a blocking read and runs the next read before committing it.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:114) clones only `HEAD`. On later rounds, [story.py](/src/forge/story.py:269) sends the diff and asks the reader to reopen the whole document, so the reader opens the old file while Forge records the read against the amended one.  
    Gain 5, Work 3, Harm 3

   Disposition: cut: the copy gets the exact hashed working-tree bytes of the plan, as Claude and Codex readers see the working tree; the test has an uncommitted-amendment case.

24. Blocking: Not done: item 4: The planned guard commands use incompatible quoting on Windows.
    Raise: Functional  
    Case: normal use - A Windows user runs a build or review with Antigravity 1.5.12 or newer.  
    The build guard uses the single-quoted shell command in [sync.py](/src/forge/sync.py:65); the review guard uses `shlex.quote` in the [plan](/plans/FORGE-ANTIGRAVITY-1.md:113). [Google’s changelog](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md) says Windows passes hook commands to `cmd.exe`, whose [quoting rules](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd) differ. The file-presence check cannot establish that either command returns Forge’s decision.  
    Gain 5, Work 3, Harm 3

   Disposition: cut: one guard command, forge hook deny, with no quotes, for builds, reads and reviews; the test runs it through the platform's shell.

25. Blocking: The cold-read retry still names a target that `forge read` cannot accept.
    Raise: Functional  
    Case: normal use - An Antigravity cold read fails because the account is signed out.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:114) supplies `forge read {doc}`, but `doc` is a file path in [story.py](/src/forge/story.py:165). `forge read` accepts a story key or slug, not that path. This leaves the earlier retry-command finding unresolved.  
    Gain 3, Work 2, Harm 3

   Disposition: cut: the retry command is forge read {target}, the story key or slug.

26. Advisory: The planned test names make the required test check fail.
    Raise: Gate  
    Case: normal use - RUNTIME finishes and runs the required cheap checks.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:54) gives every new file the same `STORY` and repeats numbers across the build, live, and review tests. [test_rules.py](/tests/test_rules.py:26) requires each number to be unique across that story, including skipped live tests.  
    Gain 4, Work 3, Harm 2
   Disposition: cut: item 3 has one test function that READS writes and REVIEW extends, and the live test has its own STORY with one test.

27. Advisory: REVIEW can start before the guard implementation it tests.
    Raise: Plan gap  
    Case: normal use - READS finishes while GUARD is still in progress.  
    [REVIEW](/plans/FORGE-ANTIGRAVITY-1.md:152) waits only for READS, but its test requires the Antigravity deny response that GUARD adds. The current [deny hook](/src/forge/deny.py:41) does not read Antigravity’s payload.  
    Gain 3, Work 1, Harm 2
   Disposition: cut: REVIEW now waits for READS and GUARD.

28. Advisory: Unproven: item 3: An Antigravity cold read works without the Claude SDK.
    Raise: Test  
    Case: normal use - A Codex user selects Antigravity for reads without installing the Claude SDK.  
    [story.py](/src/forge/story.py:241) currently sends every non-Codex reader through [Claude’s readiness check](/src/forge/worker.py:463). The planned test can pass with that check unchanged because the [repo fixture](/tests/conftest.py:599) installs a Claude SDK stand-in.  
    Gain 3, Work 3, Harm 3
   Disposition: cut: story.py uses antigravity.ready for an Antigravity reader, and the test removes the Claude SDK stand-in.

29. Advisory: Unproven: item 3: An incomplete report cannot be recorded as a clean review.
    Raise: Test  
    Case: normal use - The model returns a JSON object with an empty findings list but omits its completion status.  
    The [planned parser](/plans/FORGE-ANTIGRAVITY-1.md:120) lists the old attempt’s failure reasons, while the existing [helper](/Users/ravikiranvemula/.codex/skills/autoreview/scripts/autoreview:7469) separately validates completion and required fields. The new test supplies only a complete finding and a clean report, so it can pass if the incomplete object is accepted.  
    Gain 3, Work 3, Harm 3
   Disposition: cut: a report without a valid review_status, overall_correctness and findings list does not count; the test has a no-status case.

30. Advisory: Unproven: item 1: Usage can omit the cached-token count.
    Raise: Test  
    Case: normal use - A prompt response reports input and output tokens without a cached-read count.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:101) adds `cachedReadTokens` directly, but the [protocol type](https://agentclientprotocol.github.io/typescript-sdk/types/Usage.html) permits it to be absent or null. The stub always supplies it, so the test can pass while such a completed round fails during accounting.  
    Gain 3, Work 3, Harm 3
   Disposition: cut: missing cached and thought counts read as 0 or None; test 1 has a STUB_AGY_NO_CACHE case.

31. Advisory: Not done: item 1: The default run does not name its actual model in `forge work`.
    Raise: Not done  
    Case: normal use - A repo uses its Google plan’s default model without an override.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:98) prints the building line before the session reveals its model, so that line names `default`. The default-model test checks the run record, not what `forge work` prints.  
    Gain 3, Work 3, Harm 3
   Disposition: cut: turn prints the model and thinking level the session reports; test 1 checks the line for the plan default.

32. Advisory: Not done: item 2: A user-facing repair can keep a low effort after failure.
    Raise: Not done  
    Case: normal use - A client repo sets its Antigravity design effort to `low`, and a user-facing task needs a repair.  
    [worker.py](/src/forge/worker.py:222) applies the effort ladder only when the task is not design work. The [planned repair test](/plans/FORGE-ANTIGRAVITY-1.md:105) covers a non-design round, so it can pass while this repair stays at `low`.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - Done-when 2 promises the ladder as with Claude and Codex, whose design rounds also keep the design effort (worker.py:222); the default design effort is already high.

## Round 3

33. Blocking: Not done: item 4: A Windows checkout can replace Forge’s command guard.  
    Raise: Security  
    Case: normal use - A Windows checkout contains a `forge.cmd` file when an Antigravity worker attempts a command.  
    The [plan’s guard](/plans/FORGE-ANTIGRAVITY-1.md:98) runs `forge hook deny` without a path. [Windows searches the current directory before PATH](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/path), so it can run the checkout’s `forge.cmd` instead of Forge. That program can allow the destructive command or execute its own code. The planned test does not put a `forge.cmd` in the checkout.  
    Gain 5, Work 3, Harm 5
   Disposition: cut: the guard lives in Forge's own profile (config/hooks.json, never in the repo) and calls Forge by the absolute path of its Python, quoted with Forge's existing list2cmdline/shlex.join idiom; test 4 puts a fake forge and forge.cmd first on PATH in the checkout.

34. Blocking: Not done: item 3: A reader can open files outside its copy.  
    Raise: Security  
    Case: normal use - A review asks to read a credential file in the original checkout or the user’s home directory.  
    The [read profile](/plans/FORGE-ANTIGRAVITY-1.md:120) denies writes and commands but does not restrict reads. Forge [approves every read request](/plans/FORGE-ANTIGRAVITY-1.md:105), including an outside path for which [Antigravity asks permission](https://antigravity.google/docs/permissions?tab=cli). The file can then be sent to Google, defeating the promised copy boundary and the review’s secret-file removal.  
    Gain 5, Work 3, Harm 5
   Disposition: cut: the read profile's ask rule sends file reads to Forge, which allows only paths inside the copy, and Antigravity asks for outside reads by default; the plan states what Google documents and what the live test checks; the test has an outside-read case.

35. Blocking: Not done: item 3: Cold-read copies still contain tracked secret files.  
    Raise: Data loss  
    Case: normal use - A repository has a tracked `.env.production` file when a cold read starts.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:121) calls `isolate(copy, [])` for cold reads, so it removes no sensitive paths. Code reviews pass the helper’s sensitive-file list instead. The cold reader can therefore open and send the credential file to Google, although the owner-facing text says cold reads receive the same exclusion.  
    Gain 5, Work 2, Harm 5
   Disposition: cut: cold reads remove the same tracked_sensitive_paths as reviews, through the bundle mode that READS now adds; the test has a .env.production case.

36. Blocking: Not done: item 3: Git isolation can change the original repository.  
    Raise: Data loss  
    Case: normal use - Forge is started from a Git hook with `GIT_DIR` pointing to the original repository.  
    The new [Git isolation](/plans/FORGE-ANTIGRAVITY-1.md:118) leaves `GIT_DIR` and `GIT_WORK_TREE` in the environment. [Git documents](https://git-scm.com/docs/githooks) that hooks export these variables and that commands targeting another checkout must clear them. Forge’s planned commands to set the copy’s hook path and remove its `origin` can instead change the original repository’s configuration and remote. [Forge already clears these variables](/src/forge/repo.py:1021) for another temporary-repository operation.  
    Gain 5, Work 3, Harm 5
   Disposition: keep - the owner chose on 22 Nov 2026 to accept this as a rare limit; it is in the plan's Accepted limits.

37. Blocking: Not done: item 3: A checkout filter can run before review isolation.  
    Raise: Security  
    Case: normal use - The developer supplies a Git checkout filter through environment configuration, and the reviewed change adds a matching `.gitattributes` entry and edits that filter’s repository script.  
    The [new isolation](/plans/FORGE-ANTIGRAVITY-1.md:118) disables configuration files but leaves `GIT_CONFIG_COUNT` and its key/value variables intact. [Git applies those variables as configuration](https://git-scm.com/docs/git-config/2.38.1.html), and a configured [smudge filter runs during checkout](https://git-scm.com/book/en/v2/Customizing-Git-Git-Attributes). It can therefore execute the change’s script during clone, before `isolate` runs.  
    Gain 5, Work 3, Harm 5
   Disposition: keep - the owner chose on 22 Nov 2026 to accept this as a rare limit; it is in the plan's Accepted limits.

38. Blocking: Cold readers lose the repository’s review rules.  
    Raise: Functional  
    Case: normal use - A repository has review rules in `AGENTS.md`, and Antigravity reads a plan.  
    The [new isolation](/plans/FORGE-ANTIGRAVITY-1.md:119) removes every `AGENTS.md`. Code review receives the trusted default-branch review rules separately, but the [cold-read path](/plans/FORGE-ANTIGRAVITY-1.md:121) does not supply them. The reader is instructed to respect those rules but cannot inspect them, so it can miss required findings or raise settled ones.  
    Gain 5, Work 2, Harm 3
   Disposition: cut: the read prompt carries the default branch's Review rules, as reviews get them.

39. Blocking: Cold reads can use an outdated product brief.  
    Raise: Functional  
    Case: normal use - A coordinator changes `docs/product/BRIEF.md` without committing it, then starts a first cold read.  
    The [copy rule](/plans/FORGE-ANTIGRAVITY-1.md:121) clones `HEAD` and overlays only the plan. The [cold-read prompt](/src/forge/templates/cold-read.md:17) asks the reader to inspect the brief’s current answers, but it opens the committed version. The fix for the stale plan therefore still lets a read approve a plan against stale product answers.  
    Gain 5, Work 3, Harm 3
   Disposition: cut: the read copy is a commit of the working tree from story._snapshot, so the plan, the brief and every other input are as Claude and Codex readers see them; the test has an uncommitted-brief case.

40. Advisory: A review can change the Git environment of tests running beside it.  
    Raise: Functional  
    Case: normal use - A repository runs local close tests that need the developer’s global Git configuration.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:118) changes process-wide `os.environ` for the duration of the review. [Close runs tests in another thread](/src/forge/close.py:359), and [the test runner copies that environment](/src/forge/review.py:425). Depending on timing, tests can inherit the empty global Git configuration and fail or exercise different behavior.  
    Gain 4, Work 2, Harm 2
   Disposition: keep - the owner chose on 22 Nov 2026 to accept this as a rare limit; it is in the plan's Accepted limits.

## Round 4

41. Blocking: Not done: item 3: Alternate customization folders survive review isolation.  
    Raise: Security  
    Case: normal use - A reviewed change contains `_agents/hooks.json` with a startup hook.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:124) removes `.agents` and `.agent`, but [Antigravity also recognizes `_agents` and `_agent`](https://antigravity.google/docs/customization-discovery/). A [SessionStart hook](https://antigravity.google/docs/hooks) in one of those folders can run before the review. The stub checks only `.agents`, so the planned test misses it.  
    Gain 5, Work 2, Harm 5
   Disposition: keep - Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval

42. Blocking: Not done: item 4: The guard can import code from the checkout.  
    Raise: Security  
    Case: normal use - A checkout contains an `argparse.py` file when an Antigravity worker attempts a command.  
    The [guard](/plans/FORGE-ANTIGRAVITY-1.md:100) starts Python with `-c` from the checkout. [Python adds that directory to its import path](https://docs.python.org/3/using/cmdline.html), and [Forge’s CLI imports `argparse`](/src/forge/cli.py:2) before running the deny hook. The checkout’s file can execute and return an allow decision. The planned test plants fake executables, but no shadowed Python module.  
    Gain 5, Work 2, Harm 5
   Disposition: keep - Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval

43. Blocking: Not done: item 4: The guard’s CLI startup can run a checkout’s Git executable.  
    Raise: Security  
    Case: normal use - A Windows checkout contains a `git.cmd` when an Antigravity worker attempts a command.  
    The [new guard](/plans/FORGE-ANTIGRAVITY-1.md:100) calls `forge.cli.main()`. Before dispatching the deny hook, [CLI startup runs Git](/src/forge/cli.py:117) through [a lookup using `shutil.which`](/src/forge/repo.py:222). As [this repo’s test notes](/tests/test_rules.py:116), that lookup searches the current folder first on Windows. The checkout’s command can therefore run before the guard.  
    Gain 5, Work 2, Harm 5
   Disposition: keep - Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval

44. Blocking: Not done: item 3: A read request can have no location to check.  
    Raise: Security  
    Case: normal use - Antigravity requests permission to read an outside file but omits `toolCall.locations`.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:110) permits a read when every listed location is inside the copy, without requiring a location or checking the actual input. [ACP makes locations optional](https://agentclientprotocol.github.io/typescript-sdk/types/ToolCallUpdate.html), and [T3’s Antigravity adapter](/private/tmp/claude-501/-Users-ravikiranvemula-Workdir-symphony-forge/c01a489d-c76f-41c1-8371-d6f0052b027c/scratchpad/ext/t3code/apps/server/src/provider/acp/AntigravityProtocol.ts:297) falls back to the raw input path when none is present. An empty list can pass the planned check and allow the outside read.  
    Gain 5, Work 3, Harm 5
   Disposition: keep - Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval

45. Blocking: Not done: item 3: A snapshot can change the files the cold reader opens.  
    Raise: Functional  
    Case: normal use - A repository uses `git-crypt` to encrypt its plan or product brief in Git, and a coordinator starts another cold-read round.  
    The [new copy rule](/plans/FORGE-ANTIGRAVITY-1.md:126) builds a commit from [`_snapshot`’s Git tree](/src/forge/story.py:1124). Git applies the original repository’s clean filter while building that tree, but the clone does not receive its local smudge-filter configuration. [Git passes content through when a filter is missing](https://git-scm.com/docs/gitattributes), so the copy can contain ciphertext where the working checkout has readable text. The reader cannot reopen the current plan or brief as promised.  
    Gain 5, Work 3, Harm 3
   Disposition: keep - Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval

46. Advisory: Not done: item 4: A local-only Antigravity worker does not discover Forge’s skills.  
    Raise: Not done  
    Case: normal use - A developer selects Antigravity only in `forge.local.toml`.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:120) now permits that worker, but adds the `.codex/skills` entry only when shared `forge.toml` selects Antigravity. Its private profile has no skills entry either. The local-only test checks the guard, not whether the worker discovers the shipped skills.  
    Gain 3, Work 2, Harm 3
   Disposition: keep - Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval

47. Advisory: Not done: item 5: Doctor cannot establish both profile sign-ins over SSH.  
    Raise: Not done  
    Case: normal use - A developer uses Antigravity over SSH and has signed in to only one Forge profile.  
    [Doctor’s planned check](/plans/FORGE-ANTIGRAVITY-1.md:140) starts one session, while [builds and reads use separate profiles](/plans/FORGE-ANTIGRAVITY-1.md:99). The plan says their sign-ins are not shared over SSH, so one successful check cannot establish that both kinds of run can sign in.  
    Gain 3, Work 2, Harm 3
   Disposition: keep - Owner accepted on 22 Nov 2026: notes 41 to 45 are fixed in the builders' section (extra folder names, isolated guard start with fixed PATH, refuse reads without a location, encrypted-file care); advisory 46 and 47 stay for the builders; Astra validates the design before approval
