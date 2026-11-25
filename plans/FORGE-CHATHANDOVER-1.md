# Hand a long coordinator chat over to a fresh chat

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- A coordinator can run one new handover command that writes one short note from Forge's records: the items in flight with their state, what each one waits on, the logs to watch and the exact next commands. A fresh chat reads that one note instead of the old conversation.
- The note reuses the session-end handoff file that Forge already writes, and nothing else is added. A new client repo gets the command at setup, and an existing client repo gets it on upgrade.

## Why

A long coordinator chat rereads the whole conversation on every tool call. The owner reports one client used about 593 million Claude tokens in one day. Forge's session-end note already holds the current state, so the new work is only the on-demand command and whatever that note still lacks.

## Done when

1. **Running the handover command in a long chat writes one short note with the items in flight, their state, what each waits on, the logs to watch and the exact next commands.**
2. **A fresh chat that reads only that note can continue the work without the old conversation.**
3. **The session-end note is reused, and no second handoff file is added.**

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
