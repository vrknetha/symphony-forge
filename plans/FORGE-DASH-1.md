# Client apps get fast dashboards without hand-written queries

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- The FDE picks dashboard cards (a count, a money sum, a trend by day or week, a top-five list, or a status breakdown) over a feature's fields, and the feature command writes each card's query, scoped to the organisation.
- A card that is slow gets a summary table that background jobs keep up to date, and heavy reports use a materialized view refreshed on a schedule, shown with an Updated N minutes ago line.
- The dashboard is a fixed screen type built with shadcn charts, and the browser keeps each card's result for 30 to 60 seconds.

## Why

Client apps need dashboards built fast, but each one is hand-written with queries, and slow cards have no standard fix.

## Done when

1. **An FDE adds a dashboard with any of the five card types to a feature in one step, and each card's query is scoped to the organisation.**
2. **A card that takes about 200 ms or more gets a summary table that background jobs keep current.**
3. **A heavy report shows its data from a scheduled materialized view with an Updated N minutes ago line.**
4. **The dashboard renders with shadcn charts, and the browser reuses each card's result for 30 to 60 seconds.**
5. **Both starter apps build a dashboard with the same steps, after the feature command, database rules and job queue ship first.**

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
