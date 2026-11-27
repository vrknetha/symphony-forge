# Show model use and change size in pull requests

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Repo owners can open a task or fix pull request and see the builder model and effort, recorded token use, and delivered change size in How it went.

## Why

The current summary shows rounds, new findings, and time, but owners cannot use it to compare builders on similar work or tell how complete the token counts are.

## Done when

1. **How it went shows the builder model and effort beside the existing rounds, new review findings, and time.**
2. **Build, review, and plan read each show recorded input, cached input, and output tokens. Runs are counted once, partial coverage says how many runs reported tokens, and totals and coverage survive history compaction.**
3. **At close, the block shows product lines added plus removed and the product file count, with S through 100 lines, M from 101 through 400, L above 400, or “no product lines” for docs-only or test-only changes.**
4. **The block says “on subscription” when known and “cost unavailable” otherwise. It shows no dollar estimates and adds no board columns, reports, Forge next notices, or split rules.**
5. **New repos get the summary from their first build, and existing repos get it from their next build after upgrade.**

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
