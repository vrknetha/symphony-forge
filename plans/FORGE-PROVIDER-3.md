# Keep builds running in AWS while the laptop sleeps

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Plan now, with implementation starting after FORGE-PROVIDER-2.
- Run Claude and Codex builds in AWS sandbox boxes and resume review on the laptop when it wakes.

## Why

The current remote Codex route relies on the laptop to bring back commits and push them to GitHub, and Claude builds still run on the laptop.

## Done when

1. **Claude build rounds run on every AWS box using the developer’s one-year Claude setup token from their AWS secret store.**
2. **Codex uses the developer’s sign-in on one box at a time and writes the updated sign-in file back after each run.**
3. **One larger box runs three to four Codex rounds concurrently through one app server, and a test shows the OpenAI API key fallback works during busy periods.**
4. **With the laptop asleep, the box finishes the round, pushes the branch using the developer’s GitHub sign-in from the AWS secret store, and saves the result in S3. Forge retrieves the result and runs review when the laptop wakes.**
5. **Neon stays on the laptop unless a one-time sign-in from the box terminal works with the developer’s Neon plan.**

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
