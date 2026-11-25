# Cold reads stop churning after round one

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Advisory notes never hold a plan. From round two, only a note at Harm 4 or 5, or an earlier note still open, holds it. The code and the docs end up in one rule.
- A fix to a plan may only narrow it. A fix that adds a table, column, flow, sign-in or question becomes a defer or an owner choice, and advisory notes are not written into the plan.
- A note scored Gain 3 with Harm 3 no longer holds on its own, and a note the reader marks as rare does not hold.
- At the cold-read round limit, open notes become required builder checks with tests, with no further read and no owner question.
- New client repos get the change at setup. Existing client repos get it on upgrade, with the guide, worker brief and reader instructions updated in the same change.

## Why

Cold reads of long client plans ran 46 rounds (about 276 million tokens) across 8 reads. Round one found real defects, but later rounds were mostly churn caused by the previous round's fixes, and 85 percent of notes were held.

## Done when

1. **A plan whose notes are all advisory passes in round two with no further round. A fix that would add a table, column, flow, sign-in or question is recorded as a defer or an owner choice instead of being applied. At the round limit, open notes become builder checks with tests and no owner question is asked. Existing and new repos show the same rule after upgrade.**

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
