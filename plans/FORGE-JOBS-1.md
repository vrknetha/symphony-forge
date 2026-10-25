# Background jobs for client apps, with no Redis

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Client apps get a background job queue that runs on their existing Postgres database, so no Redis is needed.
- Both starters ship it from day one: pg-boss in the NestJS starter and Procrastinate in the Python starter.
- A separate worker process runs the jobs from the same codebase, started by Docker Compose.
- Invite emails and the CSV export run as jobs instead of inside the web request.
- Jobs retry with back-off, can run on a schedule, are safe to run twice, have a time limit and never hold a long transaction.
- Admins get a Jobs screen that lists failed jobs with a Retry button.
- The API and the worker get liveness and readiness endpoints that check the database.

## Why

Client apps need background work such as invite emails and CSV exports, with retries and schedules, but the starters have no worker and send invites and build CSV files inside the web request. Adding Redis or a second queue service to every app adds one more thing to run.

## Done when

1. **A new client app from either starter has a worker container in Docker Compose that runs an invite email job and a CSV export job from Postgres, with no Redis.**
2. **A job added in the same transaction as its data leaves no job behind when that transaction rolls back.**
3. **A failed job shows on the admin-only Jobs screen, and Retry runs it again.**
4. **The API and the worker each answer liveness and readiness checks, and readiness fails when the database is down.**
5. **The database skill lists the job rules: same-transaction enqueue, keyed idempotent jobs, time limits and no long transactions.**

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
