# Make agent-written tests prove real behaviour

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Builders name the closest existing test before writing a new one, and say what a new test adds.
- Each Done-when line names its test. Close checks that the test exists, ran and passed. Review checks that its assertion proves the line.
- A lint check blocks tests that always pass, such as assert True, and flags tests with no assertion, in pytest, Vitest and Playwright.
- For a bug fix, close runs the new test on the old code, where it must fail for the reported symptom, and on the new code, where it must pass. No minimum assertion count, no new-test limit; mutation testing comes later.

## Why

Agents add many weak tests: new tests where an existing test fits, tests with weak or no assertions, and tests shaped by code structure instead of product scenarios.

## Done when

1. **A new Forge repo and an upgraded existing repo both get the four rules, and the worker brief and close and review checks state them.**
2. **A Done-when line with no named test, or whose named test did not run or failed, makes close refuse the item with a plain message.**
3. **A tautology such as assert True or expect(x).toBe(x), and a test with no assertion, fail the lint check in a pytest, Vitest or Playwright repo.**
4. **A bug-fix test that passes on the old code, or fails on the new code, makes close refuse the fix.**

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
