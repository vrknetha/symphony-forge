# Run fewer tests on Forge pull requests

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Forge contributors wait only for the change’s own test files, the tests named in its Done when checks, and a short fixed set of basic tests.
- Forge runs the full suite once nightly on main and requires a passing full run on the release commit before each release.
- New client repositories keep the standard test setup at creation or adoption. Existing client repositories keep their configured test commands, schedules, and required checks on upgrade.

## Why

Forge tests run the real Forge command, so the related-test picker can select almost the whole suite for a small core edit. The reported close change selected 955 of 960 test files and took about two and a half hours on a laptop or 30 minutes across six GitHub runners.

## Done when

1. **A Forge pull request with a core edit runs exactly its changed test files, its named Done when tests, and the fixed basic test set, with duplicates run once.**
2. **A pull request cannot start the full suite, the nightly run on main runs it once, and a release waits for a passing full run on the release commit.**
3. **A failed full run appears under Needs you with a link to the run and opens a fix automatically through the existing failure path.**
4. **Creating or adopting a client repository uses its standard test setup, and upgrading an existing client repository preserves its test commands, schedules, and required checks.**

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
