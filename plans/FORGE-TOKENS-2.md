# Fewer costly rounds: keep the saved prompt and shorten long builder chats

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- A repair round that raises the builder's effort continues the same Codex conversation, so the saved prompt is reused instead of paid for again in full.
- A builder conversation that passes about 120K tokens is shortened, and the shortened version keeps the review findings, the failing tests and what was already tried.

## Why

A Codex repair round that goes from low to high effort loses the saved prompt: a median of 178K uncached input tokens, against 74K when effort stays the same. Long builder conversations also reread their whole history on every model call.

## Done when

1. **Uncached input per repair round is measured before and after the change on the same kind of item, and the change is reported with those numbers.**
2. **A repair round that changes effort keeps most of its cached input in the same conversation.**
3. **A builder conversation over about 120K tokens is shortened, and its findings, failing tests and tried fixes are still there afterwards.**

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
