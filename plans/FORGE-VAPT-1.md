# Client apps pass a VAPT test without per-client security work

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Sign-up, sign-in and password reset no longer reveal whether an email has an account, by message or by response time.
- Repeated failed sign-ins lock that account for a while, and new passwords are checked against a leaked-password list.
- Sessions get a new id at sign-in and end after an idle timeout, a maximum age, a password change or sign-out; cookies are HttpOnly, Secure and SameSite.
- Admins must set up an authenticator-app code with recovery codes, and members may; failed sign-ins, role changes and invites are logged as security events.
- New client repos get all of it from init; existing client repos get it on upgrade to the new release.

## Why

Client apps would fail a VAPT test today: sign-up says an account already exists, the TypeScript sign-in answers faster for unknown emails, there is no lockout, authenticator code, leaked-password check or security log, the TypeScript starter's sessions last 30 days with no idle timeout, and the nightly full run only runs tests.

## Done when

1. **Sign-up, sign-in and password reset give the same reply and similar timing for known and unknown emails, shown by a test in both starters.**
2. **An account refuses sign-in after repeated failures, shown by a test in both starters.**
3. **Each session ends on idle, maximum age, password change or sign-out, shown by a test in both starters.**
4. **Both web apps send the listed security headers with no version header, and the Python starter has the same rate limits and CSRF guard as the TypeScript one.**
5. **Admins must set up an authenticator-app code with recovery codes, and members may, shown by a test in both starters.**
6. **Each night the full run reports audit, secret, code and web-scan findings, and each finding opens a fix.**

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
