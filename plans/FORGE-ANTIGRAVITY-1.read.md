---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-22T12:01:53.374297+00:00
seconds: 1159.293
read_hash: 5ca925a351fc30fafe71e6920978bc989e42fb31
round: 2
passed: no
doc_seen: 5ca925a351fc30fafe71e6920978bc989e42fb31
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 5ffc6a080a51bb8ae7198861245a47f063d37686
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a202f2-fbec-7e52-97bc-9060b98f67be
session:
loop_choice: more
loop_reason: Owner chose on 22 Nov 2026: one more round to fix the 8 open notes, mostly review-engine safety
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

19. Blocking: Not done: item 3: Git can run a change’s hook before review isolation.
    Raise: Security  
    Case: normal use - A developer has a relative `core.hooksPath` in their Git configuration, and the change adds a `post-checkout` hook there.  
    [review.py](/src/forge/review.py:891) clones the branch before the planned isolation runs. Git runs `post-checkout` after a clone and resolves a relative hooks path in the checkout, so the change’s script can execute with the developer’s permissions. [Git hooks](https://git-scm.com/docs/githooks), [Git configuration](https://git-scm.com/docs/git-config).  
    Gain 5, Work 2, Harm 5

20. Blocking: Not done: item 3: Preparing the review diff can execute a script from the change.
    Raise: Security  
    Case: normal use - A developer’s Git configuration names a repository script as a text-conversion driver, and the change edits that script and a matching file.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:117) runs `git diff --no-ext-diff` before isolation. Git still runs text-conversion drivers unless `--no-textconv` is given; the pinned [review helper](/Users/ravikiranvemula/.codex/skills/autoreview/scripts/autoreview:52) uses that flag. [Git diff documentation](https://git-scm.com/docs/git-diff).  
    Gain 5, Work 2, Harm 5

21. Blocking: Not done: item 3: A reviewed `AGENTS.md` becomes instructions for its reviewer.
    Raise: Security  
    Case: normal use - A change edits `AGENTS.md` to tell the reviewer to suppress a finding.  
    The [isolation rule](/plans/FORGE-ANTIGRAVITY-1.md:113) leaves that file in the review checkout as “text.” [Google’s rules documentation](https://antigravity.google/docs/rules) says Antigravity automatically loads it as an always-active rule. The existing [review helper](/Users/ravikiranvemula/.codex/skills/autoreview/scripts/autoreview:3897) instead tells reviewers that source files are evidence, not instructions.  
    Gain 5, Work 3, Harm 5

22. Blocking: Not done: item 3: A reader can change the original checkout from its throwaway copy.
    Raise: Security  
    Case: normal use - A developer has an Antigravity allow rule for writing files outside the active workspace.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:113) changes the working directory and removes the copy’s remote, but does not restrict writes to that directory. [Google’s permissions](https://antigravity.google/docs/permissions?tab=cli) permit rules such as `write_file(*)` without a request. The [snapshot check](/src/forge/story.py:369) does not undo a write; an ignored file can escape its snapshot altogether. The planned test writes only inside the copy.  
    Gain 5, Work 4, Harm 5

23. Blocking: Not done: item 3: A later cold read opens the old committed plan.
    Raise: Functional  
    Case: normal use - The coordinator amends a plan after a blocking read and runs the next read before committing it.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:114) clones only `HEAD`. On later rounds, [story.py](/src/forge/story.py:269) sends the diff and asks the reader to reopen the whole document, so the reader opens the old file while Forge records the read against the amended one.  
    Gain 5, Work 3, Harm 3

24. Blocking: Not done: item 4: The planned guard commands use incompatible quoting on Windows.
    Raise: Functional  
    Case: normal use - A Windows user runs a build or review with Antigravity 1.5.12 or newer.  
    The build guard uses the single-quoted shell command in [sync.py](/src/forge/sync.py:65); the review guard uses `shlex.quote` in the [plan](/plans/FORGE-ANTIGRAVITY-1.md:113). [Google’s changelog](https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md) says Windows passes hook commands to `cmd.exe`, whose [quoting rules](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmd) differ. The file-presence check cannot establish that either command returns Forge’s decision.  
    Gain 5, Work 3, Harm 3

25. Blocking: The cold-read retry still names a target that `forge read` cannot accept.
    Raise: Functional  
    Case: normal use - An Antigravity cold read fails because the account is signed out.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:114) supplies `forge read {doc}`, but `doc` is a file path in [story.py](/src/forge/story.py:165). `forge read` accepts a story key or slug, not that path. This leaves the earlier retry-command finding unresolved.  
    Gain 3, Work 2, Harm 3

26. Advisory: The planned test names make the required test check fail.
    Raise: Gate  
    Case: normal use - RUNTIME finishes and runs the required cheap checks.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:54) gives every new file the same `STORY` and repeats numbers across the build, live, and review tests. [test_rules.py](/tests/test_rules.py:26) requires each number to be unique across that story, including skipped live tests.  
    Gain 4, Work 3, Harm 2
   Disposition: keep - below the bar (follow-up)

27. Advisory: REVIEW can start before the guard implementation it tests.
    Raise: Plan gap  
    Case: normal use - READS finishes while GUARD is still in progress.  
    [REVIEW](/plans/FORGE-ANTIGRAVITY-1.md:152) waits only for READS, but its test requires the Antigravity deny response that GUARD adds. The current [deny hook](/src/forge/deny.py:41) does not read Antigravity’s payload.  
    Gain 3, Work 1, Harm 2
   Disposition: keep - below the bar (follow-up)

28. Advisory: Unproven: item 3: An Antigravity cold read works without the Claude SDK.
    Raise: Test  
    Case: normal use - A Codex user selects Antigravity for reads without installing the Claude SDK.  
    [story.py](/src/forge/story.py:241) currently sends every non-Codex reader through [Claude’s readiness check](/src/forge/worker.py:463). The planned test can pass with that check unchanged because the [repo fixture](/tests/conftest.py:599) installs a Claude SDK stand-in.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

29. Advisory: Unproven: item 3: An incomplete report cannot be recorded as a clean review.
    Raise: Test  
    Case: normal use - The model returns a JSON object with an empty findings list but omits its completion status.  
    The [planned parser](/plans/FORGE-ANTIGRAVITY-1.md:120) lists the old attempt’s failure reasons, while the existing [helper](/Users/ravikiranvemula/.codex/skills/autoreview/scripts/autoreview:7469) separately validates completion and required fields. The new test supplies only a complete finding and a clean report, so it can pass if the incomplete object is accepted.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

30. Advisory: Unproven: item 1: Usage can omit the cached-token count.
    Raise: Test  
    Case: normal use - A prompt response reports input and output tokens without a cached-read count.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:101) adds `cachedReadTokens` directly, but the [protocol type](https://agentclientprotocol.github.io/typescript-sdk/types/Usage.html) permits it to be absent or null. The stub always supplies it, so the test can pass while such a completed round fails during accounting.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

31. Advisory: Not done: item 1: The default run does not name its actual model in `forge work`.
    Raise: Not done  
    Case: normal use - A repo uses its Google plan’s default model without an override.  
    The [plan](/plans/FORGE-ANTIGRAVITY-1.md:98) prints the building line before the session reveals its model, so that line names `default`. The default-model test checks the run record, not what `forge work` prints.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)

32. Advisory: Not done: item 2: A user-facing repair can keep a low effort after failure.
    Raise: Not done  
    Case: normal use - A client repo sets its Antigravity design effort to `low`, and a user-facing task needs a repair.  
    [worker.py](/src/forge/worker.py:222) applies the effort ladder only when the task is not design work. The [planned repair test](/plans/FORGE-ANTIGRAVITY-1.md:105) covers a non-design round, so it can pass while this repair stays at `low`.  
    Gain 3, Work 3, Harm 3
   Disposition: keep - below the bar (follow-up)
