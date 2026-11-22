# Tell clients what each Forge release changed

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Each release ships its notes as a file inside Forge, so they install with it and need no network. A new client repo gets them from its first install; an existing client repo gets them on its next upgrade.
- The upgrade output lists the changes of every release between the old version and the new one.
- The next command shows those changes once to the agent, so the agent can tell the owner and adjust.
- The sync command writes the open known issues, with their workarounds, into a section of the shipped guide, taken from the notes files. An issue that a later release fixes drops out. Release notes must be written so an agent can act on them.

## Why

Clients do not learn what each Forge release changed. Release notes live only on GitHub, and the upgrade, sync and next commands print none. After an upgrade, neither the agent nor the person knows the new features, fixes or known issues.

## Done when

1. **A release cannot be cut without its notes file inside Forge.**
2. **After an upgrade, the output lists the changes of every release between the old and the new version.**
3. **The next step shows the new release's changes once to the agent, and not again on later runs.**
4. **The shipped guide has a known-issues section with each open issue's workaround, and a fixed issue is gone after the release that fixes it.**

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
