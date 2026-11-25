# Finished work is cleaned up every time, and leftover work is listed with one next step

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Every Forge command tidies merged work on this machine. It removes the folder and local branch of each merged item that has no uncommitted files and whose local branch still points at the merged pull request's last commit, then prints one line with the count. The rule reuses the check forge doctor already makes before it removes a folder (src/forge/doctor.py, _finished), and keeps the merge rule that a folder with later local commits stays (src/forge/merge.py, the advanced check). Owner's wording "no uncommitted changes" alone would drop that protection, so the story must keep it.
- The session-start context hook gets the same tidy-up. Decision 0093 says host hooks only block destructive commands, capture approval and load context, and forge hook context is marked read-only (src/forge/nextstep.py, changes_state False). The story must decide whether the hook may delete folders, or whether the tidy-up runs only inside the Forge command the hook calls.
- forge next shows every unmerged leftover in one block, with one next step each: land it, or drop it with a reason. A clean folder whose pull request closed without merge is removed only when its branch is still on GitHub, because otherwise removing it deletes the only copy of that work (doctor's existing check does not test this). A folder with uncommitted files is never removed.
- forge land with no item, in a repo where the agent merges, drives every open item to merge, including items whose builder stopped, and collects the owner's decisions (round limit, approval) into one list at the end. Today src/forge/land.py refuses when no item and no all option is given, so this changes the command's interface. It overlaps the pending FORGE-LAND-1 story, which the story doc should name.
- The overlap with the pending FORGE-DOCTORFIX-1 story (doctor repairs, including removing folders of finished work) must be stated, so the two do not both change the same removal code without a plan.
- A new client repo and an existing client repo both get these rules on upgrade. Each ordinary rule gets one test on a new repo. Coordinator-facing steps update src/forge/templates/skill.md in the same change, as the review rules require.

## Why

Forge removes a folder only when forge merge runs on the same machine, so finished folders pile up. The owner reports about 115 local folders in one client repo, and on one machine 8 of 10 leftover folders belonged to pull requests already merged elsewhere.

## Done when

1. **After any Forge command, merged work with no uncommitted files and no local commits beyond its merged pull request is removed, and one line says how many were removed.**
2. **forge next lists every unmerged leftover in one block, with one next step for each.**
3. **A folder with uncommitted files, or with local commits its pull request does not have, is never removed.**
4. **In a repo where the agent merges, forge land with no item merges every open item and ends with one list of the owner's decisions.**

## Risks

<!-- Each one-way step: deleting data, a destructive migration, a new vendor. -->

Risks: none

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

### Done-when details

<!-- Under each Done-when item's number: its evidence, edge cases and the tests that prove it.
Workers and reviewers get the entries of the items they cover. An item with nothing to add has
no entry. -->

1. <Evidence, edge cases and the tests that prove item 1.>

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

New moving parts: none

## Notes
