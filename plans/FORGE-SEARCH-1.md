# One search across the whole app

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- From the top bar, a person searches every page, action and record they can view in one box, with the best results from each module.
- On a module's own page, the top-bar search starts on that module's results.
- Each new feature's name and text fields become searchable, with its status shown under each result.

## Why

Each list has its own search and nothing searches the whole app at once; the Ctrl+K panel only lists pages and actions today. This needs the feature command and the database rules to come first.

## Done when

1. **Typing two or more characters in the top bar opens the Ctrl+K panel with pages and actions first, then up to five results for each module the person can view, with All and per-module chips.**
2. **On a module's page the panel starts on that module, and results appear 150 ms after typing stops.**
3. **Creating, changing or deleting a record updates its search entry, and a rebuild command refills search from every module.**

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
it may change. Tests: the tests it adds or changes. After: the tasks it waits for. When two tasks
share a function, field, file format or command, the first task pins it: it commits the shared
names and stubs plus one test that crosses both sides, and the tasks that use it list it under
After. Split tasks so each owns its files; shared lines (command table, guide list, registry) go
to one task or a small last wiring task; After only when a task needs another task's code. The
Developer column is optional: the lead fills or changes a GitHub username here, below For the
builders, without another approval. Leave it blank for an unassigned part. Forge next uses
the caller's GitHub login; another developer may start it with a warning. Existing tables
without Developer still work. The moving-parts line stays last: "none", or each new dependency, service, datastore,
queue, background job or abstraction layer, with the Done-when item that needs it. -->

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|

New moving parts: none

## Notes
