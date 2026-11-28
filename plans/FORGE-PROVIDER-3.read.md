---
reader: codex (gpt-6.1-terra)
read_at: 2026-11-28T04:26:01.879588+00:00
seconds: 867.854
read_hash: 68416d82fb376e9a8881add25d3d8359632c6cd3
round: 2
passed: no
doc_seen: 68416d82fb376e9a8881add25d3d8359632c6cd3
spec_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
notes_seen: 4274ead1d37000bd438f70c4b36806c2d3077075
answers_seen: e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
conversation: 01a21ff9-89ae-7012-a3e2-a0bb172d857a
session:
loop_choice: accept
loop_reason: Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)
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

1. **Blocking: Not done: item 2: A developer can request another developer’s sign-ins.**  
   Raise: Security  
   Case: normal use - two developers use the same AWS setup.  
   [The claim](/plans/FORGE-PROVIDER-3.md:76) takes a developer ID from its caller and uses that same ID for the session tag and secret check. It does not bind the ID to the caller’s AWS identity. A caller with claim and session access can name another developer and obtain that developer’s credentials. The test supplies only honest IDs.  
   Gain 5, Work 4, Harm 5
   Disposition: cut - round verbs now go to a signed (`AWS_IAM`) function URL and the Lambda takes the developer only from the caller's verified identity, never the payload; proved in `test_2` (a payload naming developer 2 from developer 1 still gets developer 1's values) and `test_1` (the template has the `AWS_IAM` URL).

2. **Blocking: Not done: item 2: Credentials can enter the stored round log.**  
   Raise: Security  
   Case: normal use - a failing command prints its environment or an authentication diagnostic.  
   [The plan](/plans/FORGE-PROVIDER-3.md:81) uploads driver output without a redaction step. The current [Claude driver](/src/forge/claude_turn.py:19) serializes messages and diagnostics without removing secrets. The proposed stub never prints a credential, so it can pass while a real log retains one in S3.  
   Gain 5, Work 3, Harm 5
   Disposition: cut - every log chunk goes through an exact-string filter for each secret the round holds (raw and base64) before upload, and the stub prints its environment and an auth error with the token; proved in `test_2`.

3. **Blocking: Not done: item 2: AWS cannot issue the specified round credentials.**  
   Raise: Functional  
   Case: normal use - the first round claims a box.  
   [The plan](/plans/FORGE-PROVIDER-3.md:64) grants `sts:AssumeRole`, then [requests](/plans/FORGE-PROVIDER-3.md:76) a tagged session lasting three hours. AWS limits a role assuming another role to one hour and requires `sts:TagSession` for the tag. The plan also does not specify the target role’s permissions; the session policy alone cannot grant them. The claim therefore fails or produces credentials unable to do the work. [AWS role chaining](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_roles.html), [session tags](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html), [session policies](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html).  
   Gain 5, Work 4, Harm 3
   Disposition: cut - the AWS role sessions are gone. The Lambda copies one developer's values into a one-use secret per round, so no one-hour chaining limit, session tag or target-role policy applies; proved in `test_2`.

4. **Blocking: Not done: item 2: A new box cannot download the script that gives it S3 access.**  
   Raise: Functional  
   Case: normal use - a round starts on a newly launched box.  
   [The instance role](/plans/FORGE-PROVIDER-3.md:76) has no S3 permission. The prescribed SSM command must fetch `round.sh` from S3, but [that script](/plans/FORGE-PROVIDER-3.md:80) is what first reads the temporary credentials that have S3 access.  
   Gain 5, Work 2, Harm 3
   Disposition: cut - `RoundMachineRole` has `s3:GetObject` on `rounds/*/in/*` and `s3:PutObject` on `rounds/*/out/*` (no list right), so a new box can fetch `round.sh`; checked in `test_1`'s template test and used in `test_2`.

5. **Blocking: Not done: item 3: The first Codex sign-in has no specified credentials for saving its file.**  
   Raise: Functional  
   Case: normal use - a developer signs in to Codex for the first time.  
   [The terminal helper](/plans/FORGE-PROVIDER-3.md:90) must write the sign-in secret, but the instance role cannot write it and the plan obtains the scoped credentials inside `round.sh`, which this interactive setup does not run. The test checks that the session command is printed, not that the helper saves a file.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - the sign-in helper writes to a `-back` secret named in its own one-use session secret, and `round-release` copies it into the developer's `codex-signin`; proved in `test_3`.

6. **Blocking: Not done: item 2: A second round packed onto a box cannot obtain its own credentials.**  
   Raise: Functional  
   Case: normal use - two Claude rounds from the same developer share a box.  
   [The plan](/plans/FORGE-PROVIDER-3.md:75) permits both rounds, but puts each one-use secret’s name only in instance user data. User data is set when the instance launches; the second claim cannot put its different secret name there. The first session’s S3 access is restricted to the first round.  
   Gain 4, Work 3, Harm 3
   Disposition: cut - the session secret name travels in each round's own SSM start command, not in user data, so a second round on the same box has its own; proved in `test_2` (two rounds share a box).

7. **Blocking: Not done: item 2: A busy laptop can wait before it reaches box routing.**  
   Raise: Functional  
   Case: normal use - the laptop has no free worker place.  
   [The proposed routing call](/plans/FORGE-PROVIDER-3.md:68) comes after the brief is built, while the current [worker](/src/forge/worker.py:261) waits for a laptop place before building that brief. It can therefore wait indefinitely instead of sending the round to a box.  
   Gain 5, Work 3, Harm 3
   Disposition: cut - `aws_rounds.choose` now runs after `codex.hold` and before `machine.agent_slot`, so a busy laptop never waits first, and the brief is built without a laptop place; proved in `test_1`.

8. **Blocking: Not done: item 2: The box receives a brief with laptop-only paths.**  
   Raise: Functional  
   Case: normal use - a round moves from a developer’s laptop to Linux.  
   [The plan](/plans/FORGE-PROVIDER-3.md:80) sends the laptop-built brief unchanged. [The brief builder](/src/forge/worker.py:610) puts the laptop’s absolute checkout path in it and also names the laptop’s installed standards and conventions paths. Those paths need not exist on the box.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `worker._brief` takes a `box` argument that writes the box checkout path and `{forge_home}` for laptop-only paths; the builder lists and tests every laptop path; proved in `test_2`.

9. **Blocking: Gate: A fresh box clone has none of Forge’s Git checks.**  
   Raise: Gate  
   Case: normal use - a box worker commits a fix.  
   [The clone steps](/plans/FORGE-PROVIDER-3.md:78) do not install the Git hooks. The existing [pre-commit hook](/src/forge/githooks.py:154) enforces the fix-size and interface rules; the planned outgoing check does not replace those checks. A box can commit and push a fix that should have stopped for promotion.  
   Gain 4, Work 2, Harm 3
   Disposition: cut - `round.sh` installs the repo's Git hooks in the clone, and the Git hook refusing a fix-size breach in the box is a case in `test_2`.

10. **Blocking: Not done: item 2: The stop test bypasses `forge stop`.**  
    Raise: Test  
    Case: normal use - the owner stops a running box round.  
    [The test](/plans/FORGE-PROVIDER-3.md:85) writes `in/stop` directly. The current [stop command](/src/forge/machine.py:632) acts on local lane entries, and the RESULT task does not change it to write that object. The test can pass while the real command never asks the box to push.  
    Gain 4, Work 2, Harm 3
   Disposition: cut - the stop path now goes through `machine.stop` (RESULT's scope includes `machine.py`), and `test_2` stops with `forge stop <item>`, not by writing `in/stop` directly.

11. **Blocking: Not done: item 2: Stopping one round can destroy another round’s work.**  
    Raise: Data loss  
    Case: normal use - two rounds share a box and the owner stops one.  
    [The plan](/plans/FORGE-PROVIDER-3.md:75) packs two rounds onto one machine, but [stop](/plans/FORGE-PROVIDER-3.md:20) ends that machine. The other round can lose its unpushed commits and uncommitted work without receiving its own bounded push.  
    Gain 5, Work 3, Harm 5
   Disposition: cut - stop is per round: that round's `in/stop`, then `ssm cancel-command` for that round's command only; the box is never ended by stop, so a second round on the box goes on; proved in `test_2`.

12. **Blocking: Not done: item 4: A failed trial does not stop the shared-box task.**  
    Raise: Plan gap  
    Case: normal use - the trial records “no.”  
    [SHARED depends only on TRIAL](/plans/FORGE-PROVIDER-3.md:126), and the test explicitly says the code does not read the trial result as a switch. The existing [background runner](/src/forge/runner.py:476) starts ready parts automatically. The plan gives no working way to stop SHARED before it starts or to rewire NEON after a “no.”  
    Gain 5, Work 2, Harm 3
   Disposition: cut - SHARED is removed from this story. The story builds the trial (it can say no) and the key fallback; the sharing is a follow-up story if the trial says yes, so no part can start without the owner's choice. Done when 4, the Tasks table and the Notes match.

13. **Blocking: Not done: item 3: An old completion mark can free a new Codex lease.**  
    Raise: Data loss  
    Case: normal use - a warm box runs a second Codex round after its first finishes.  
    [The lease rule](/plans/FORGE-PROVIDER-3.md:91) frees a lease when the machine item shows `rounds_done`, but does not clear that mark or tie it to the current lease. The first round’s mark can free the second round’s lease, allowing concurrent use and conflicting refreshes of the same sign-in.  
    Gain 4, Work 2, Harm 4
   Disposition: cut - the lease has its own random `id`, the box lists finished lease ids in `rounds_done`, and `tick` frees a lease only when its own id is listed; proved in `test_3` (a warm box's second round).

14. **Blocking: Not done: item 2: The outgoing check rejects work Forge currently permits.**  
    Raise: Functional  
    Case: normal use - a task needs an unlisted caller, or a settings fix changes `forge.toml`.  
    [The plan](/plans/FORGE-PROVIDER-3.md:82) rejects every commit outside Scope and every protected-settings change, even when `keep_settings` is true. The existing [worker brief](/src/forge/templates/brief.md:199) permits necessary files outside Scope, and authorized settings fixes are valid work. Fixes also have no task Scope to check.  
    Gain 4, Work 2, Harm 3
   Disposition: cut - the box now checks only that the new commits sit on top of `start` and do not change a protected setting unless `keep_settings`; Scope stays the laptop review's job, so out-of-Scope files and settings fixes are pushed; proved in `test_2`.

15. **Blocking: Not done: item 2: A question-only round cannot create the required bundle.**  
    Raise: Functional  
    Case: normal use - a worker asks a question before making a commit.  
    [The result steps](/plans/FORGE-PROVIDER-3.md:82) unconditionally create a bundle of new commits before writing the result. Git refuses an empty bundle, so the question can be lost instead of reaching `forge work`. The proposed question test does not require the stub to leave the branch unchanged. [Git bundle documentation](https://git-scm.com/docs/git-bundle.html).  
    Gain 4, Work 1, Harm 3
   Disposition: cut - the bundle is created only when there are new commits; a question-only round writes none; proved in `test_2`.

16. **Blocking: Plan gap: `commit` is not defined for result reconciliation.**  
    Raise: Plan gap  
    Case: normal use - the box makes and pushes a commit.  
    [The request](/plans/FORGE-PROVIDER-3.md:78) calls the starting tip `commit`; the result also has a `commit` field, and [reconciliation](/plans/FORGE-PROVIDER-3.md:83) compares the pushed tip with `commit` without defining which one it means. Comparing with the starting tip rejects every successful round that made a commit.  
    Gain 4, Work 1, Harm 3
   Disposition: cut - the request field is now `start` (the starting tip) and the result field is `tip`; reconciliation compares origin's tip with the result's `tip`; proved in `test_2`.

17. **Blocking: Plan gap: SIGNIN must build roles whose rules it does not receive.**  
    Raise: Plan gap  
    Case: normal use - the first builder starts SIGNIN.  
    [SIGNIN’s details](/plans/FORGE-PROVIDER-3.md:64) assign both roles by reference to entry 2. The current [brief builder](/src/forge/worker.py:636) includes detailed entries only for covered items, and SIGNIN covers item 1. Its builder therefore does not receive the role trust and access rules it must implement.  
    Gain 4, Work 1, Harm 2
   Disposition: cut - the role, control address, policy and secret rules now sit in entry 1's own bullets, which SIGNIN's builder receives; checked in `test_1`'s template test.

18. **Blocking: Not done: AWS status has no work assigned to count box rounds.**  
    Raise: Not done  
    Case: normal use - the owner checks a week containing box rounds.  
    [The story promises round minutes](/plans/FORGE-PROVIDER-3.md:24), but none of its tasks adds round accounting to status or tests it. The reused [story 2 status rule](/Users/ravikiranvemula/Workdir/symphony-forge-story-FORGE-PROVIDER-2/plans/FORGE-PROVIDER-2.md:103) counts test boxes. The promised cost comparison can omit or misclassify build rounds.  
    Gain 4, Work 2, Harm 2
   Disposition: cut - RESULT's scope adds `aws.py` and `admit.mjs`: `round-release` writes `done#` for rounds and `status` prints rounds, minutes, cost and unused time per branch; proved in `test_2`.

19. **Blocking: Round boxes have no idle shutdown rule.**  
    Raise: Scale  
    Case: normal use - one 40-minute round finishes and no other round uses that box.  
    [Story 2’s idle rule](/Users/ravikiranvemula/Workdir/symphony-forge-story-FORGE-PROVIDER-2/plans/FORGE-PROVIDER-2.md:89) applies to `test` slots, while this plan adds `round` slots without extending it. A released round box can remain until its roughly 175-minute shutdown, costing about $0.58 at the plan’s rate instead of the stated $0.14 and retaining a machine place.  
    Adds work: extend idle termination to round slots; F 3 x H 2 = 6; 2 x C = 4  
    Gain 4, Work 2, Harm 2
   Disposition: cut - story 2's idle rule now covers `round` slots (600 s with no work, kept while a lease copy-back is pending); proved in `test_2`.

20. **Blocking: Gate: `Design: none` covers a new sign-in flow.**  
    Raise: Gate  
    Case: normal use - a developer enables box rounds and saves a sign-in.  
    [The story](/plans/FORGE-PROVIDER-3.md:26) chooses no design because the steps appear in a terminal, but SIGNIN adds a multi-step flow for the person. The supplied read rules require a design for a part that changes a flow.  
    Gain 4, Work 1, Harm 2
   Disposition: cut - the Design line now says the sign-in flow is printed text only and points to the exact lines in the Done-when details; the flow has no screen.

21. **Blocking: Gate: The new commands and steps ship before their guide update.**  
    Raise: Gate  
    Case: normal use - SIGNIN merges before the later parts.  
    [SIGNIN](/plans/FORGE-PROVIDER-3.md:120) adds a setting and sign-in command, but the guide is deferred to [NEON](/plans/FORGE-PROVIDER-3.md:127). The repository’s [review rule](/AGENTS.md:139) requires the coordinator or worker guide in the same change.  
    Gain 4, Work 1, Harm 2
   Disposition: cut - SIGNIN now writes the first guide section and every later part that adds a command or step edits it in its own change (each part's scope lists the guide files); NEON adds only the Neon lines; checked in `test_1` and `test_6`.

Not checked: real AWS execution. `forge next` could not finish in the read-only sandbox.

## Round 2

22. **Blocking: Not done: item 2: A developer can send commands to another developer’s round box.**  
    Raise: Security  
    Case: normal use - two developers use the same AWS setup.  
    [Story 2’s policy](/Users/ravikiranvemula/Workdir/symphony-forge-story-FORGE-PROVIDER-2/plans/FORGE-PROVIDER-2.md:84) permits `ssm:SendCommand` on every instance with the stack tag. [This plan](/plans/FORGE-PROVIDER-3.md:64) leaves that permission in place and relies on the guide to restrict access. A developer can run a command on another developer’s round box and read its sign-ins, without impersonating its claim.  
    Gain 5, Work 3, Harm 5
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

23. **Blocking: Not done: item 2: A developer can replace another developer’s round script.**  
    Raise: Security  
    Case: normal use - two developers use the same AWS setup.  
    [Story 2’s policy](/Users/ravikiranvemula/Workdir/symphony-forge-story-FORGE-PROVIDER-2/plans/FORGE-PROVIDER-2.md:84) gives developers list and write access to the shared bucket. [The new round](/plans/FORGE-PROVIDER-3.md:79) runs a script stored there. Another developer can list and replace that script before it runs, causing it to disclose the round owner’s sign-ins.  
    Gain 5, Work 3, Harm 5
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

24. **Blocking: Not done: item 2: Direct invocation can forge the control URL’s caller identity.**  
    Raise: Security  
    Case: normal use - two developers use the same AWS setup.  
    [Story 2](/Users/ravikiranvemula/Workdir/symphony-forge-story-FORGE-PROVIDER-2/plans/FORGE-PROVIDER-2.md:84) lets developers invoke `webhook` directly with an event they supply. [The new control path](/plans/FORGE-PROVIDER-3.md:62) trusts `requestContext.authorizer.iam.userId` in that event but specifies no check that it came through the authenticated URL. A direct caller can supply that field for another developer; the new test exercises only a signed URL call.  
    Gain 5, Work 3, Harm 5
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

25. **Blocking: Not done: item 1: A developer can retag another developer’s secret.**  
    Raise: Security  
    Case: normal use - two developers save sign-ins in the same stack.  
    [The setup policy](/plans/FORGE-PROVIDER-3.md:64) permits `TagResource` on every developer’s secret when the *requested* developer tag equals the caller. A caller can therefore replace another secret’s developer and stack tags. [Turn-off](/plans/FORGE-PROVIDER-3.md:66) then misses that secret when it filters by the original stack tag.  
    Gain 5, Work 2, Harm 4
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

26. **Blocking: Not done: item 2: The new filter can leave a Codex sign-in in the log.**  
    Raise: Security  
    Case: normal use - a diagnostic prints the JSON sign-in file.  
    [The filter](/plans/FORGE-PROVIDER-3.md:80) matches the complete file as raw text or base64. The [Codex driver](/src/forge/codex_turn.py:44) serializes output as JSON, escaping the file’s quotes and newlines. Neither complete-file string matches that encoded output, so its credentials can reach S3. The proposed filter test prints a Claude token, not an encoded sign-in file.  
    Gain 5, Work 3, Harm 5
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

27. **Blocking: Not done: item 2: The webhook lacks permission to launch a round box.**  
    Raise: Functional  
    Case: normal use - the first round needs a new box.  
    [Story 2](/Users/ravikiranvemula/Workdir/symphony-forge-story-FORGE-PROVIDER-2/plans/FORGE-PROVIDER-2.md:83) grants the webhook permission for its test role and launch template. [The new stack rules](/plans/FORGE-PROVIDER-3.md:64) add neither `iam:PassRole` for `RoundMachineRole` nor `ec2:RunInstances` on its launch template. The [claim](/plans/FORGE-PROVIDER-3.md:75) therefore cannot launch it with the specified permissions. [AWS instance-role permissions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/permission-to-pass-iam-roles.html).  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

28. **Blocking: Not done: item 2: The Lambda cannot create the tagged session secret.**  
    Raise: Functional  
    Case: normal use - a round is placed.  
    [The plan](/plans/FORGE-PROVIDER-3.md:64) grants the Lambda `CreateSecret` but not `TagResource` on `forge-session/`. AWS requires both when creating a tagged secret. Creating it without the tag would instead make [turn-off’s tag filter](/plans/FORGE-PROVIDER-3.md:66) miss it. [AWS CreateSecret](https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_CreateSecret.html).  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

29. **Blocking: Not done: item 1: The setup policy denies sign-in checks and updates.**  
    Raise: Functional  
    Case: normal use - a developer saves or replaces a sign-in.  
    [The policy](/plans/FORGE-PROVIDER-3.md:64) requires `aws:RequestTag/forge-developer` for `ListSecretVersionIds` and `PutSecretValue`. Those requests do not carry tags, so the condition is not met. The [sign-in command](/plans/FORGE-PROVIDER-3.md:65) cannot verify a first save or update an existing value under that policy. [AWS condition keys](https://docs.aws.amazon.com/service-authorization/latest/reference/list_secretsmanager.html).  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

30. **Blocking: Not done: item 2: The control alias lacks a required invoke permission.**  
    Raise: Functional  
    Case: normal use - the laptop makes its first control request.  
    [The plan](/plans/FORGE-PROVIDER-3.md:64) adds `lambda:InvokeFunctionUrl` on `control`, while story 2 grants `lambda:InvokeFunction` on the unqualified webhook. AWS requires both permissions for a new function URL, and an unqualified function permission does not cover a qualified alias. [AWS URL permissions](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html), [AWS function ARN permissions](https://docs.aws.amazon.com/lambda/latest/dg/lambda-api-permissions-ref.html).  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

31. **Blocking: Not done: item 3: The setup policy cannot start the sign-in session.**  
    Raise: Functional  
    Case: normal use - a developer signs in to Codex for the first time.  
    [The sign-in steps](/plans/FORGE-PROVIDER-3.md:90) require `aws ssm start-session`, but [the new developer policy](/plans/FORGE-PROVIDER-3.md:64) does not grant `ssm:StartSession` or the data-channel permission. Story 2 grants command permissions, not session permissions. [AWS session policy example](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-default-session-document.html).  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

32. **Blocking: Not done: item 3: The Lambda cannot read the sign-in copy-back secret.**  
    Raise: Functional  
    Case: normal use - the first Codex sign-in finishes, or a Codex round refreshes it.  
    [The copy-back steps](/plans/FORGE-PROVIDER-3.md:90) require the Lambda to read `forge-session/...-back`. [Its policy](/plans/FORGE-PROVIDER-3.md:64) grants `GetSecretValue` only on `forge-<RepoId>/*`, so the copy cannot occur and the refreshed sign-in cannot be saved before release.  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

33. **Blocking: Not done: item 3: The interactive helper is not given its session secret name.**  
    Raise: Functional  
    Case: normal use - a developer signs in to Codex for the first time.  
    [A round](/plans/FORGE-PROVIDER-3.md:75) receives its session token in its SSM command, and the machine’s user data has no session name. The [interactive steps](/plans/FORGE-PROVIDER-3.md:90) start only a shell and run `keep-signin codex` without that token. The helper has no specified way to find the session or its `-back` secret.  
    Gain 5, Work 2, Harm 3
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

34. **Blocking: Not done: item 1: Deleted session copies can remain after AWS is turned off.**  
    Raise: Security  
    Case: normal use - a round ends, then the developer turns AWS off.  
    [The round](/plans/FORGE-PROVIDER-3.md:80) deletes its one-use secret without specifying immediate deletion. AWS normally schedules deletion with a recovery window, and [the planned `list-secrets` call](/plans/FORGE-PROVIDER-3.md:66) excludes secrets already scheduled for deletion. Turn-off can report completion while recoverable copies of sign-ins remain. [AWS deletion](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_delete-secret.html), [AWS list-secrets](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/list-secrets.html).  
    Gain 4, Work 2, Harm 4
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)

35. **Advisory: Not done: item 2: Round boxes cannot read approved test files.**  
    Raise: Functional  
    Case: normal use - a repository’s tests need an approved test file.  
    [The round steps](/plans/FORGE-PROVIDER-3.md:77) say the box reads story 2’s test-files secret. Neither [the round role nor the Lambda role](/plans/FORGE-PROVIDER-3.md:64) can read that secret, and the session copy contains only the GitHub and provider sign-ins. The planned test can pass without running a test that needs an approved file.  
    Gain 4, Work 2, Harm 3

Not checked: real AWS execution. `forge next` could not finish in the read-only sandbox.
   Disposition: keep - Owner accepted; note 22 becomes a must-fix line (owner tag on each box, commands allowed only on your own boxes)
