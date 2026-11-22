---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-22T11:25:05.158723+00:00
seconds: 897.27
read_hash: 09ab4da67a31f871a56a3ac3266c94d5ef771f06
round: 1
passed: no
doc_seen: 09ab4da67a31f871a56a3ac3266c94d5ef771f06
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a202f2-fbec-7e52-97bc-9060b98f67be
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
