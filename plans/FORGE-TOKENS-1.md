# Builder rounds send fewer input tokens

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- First, with no behaviour change: record a baseline of input tokens and model requests per build and repair round from the run records, counting commit nudges and capacity retries.
- Next, send a large diff (over 2,000 characters) or a long related-test list as file names with a size note, keeping required tests and failing check names inline.
- Then, a fresh build brief keeps scope, Done when, the rules that apply, and the proof and commit steps inline, and names the standards file, non-UI design notes and release history as files the worker opens when needed.
- Last, a repair round starts fresh with a compacted brief (findings, failing tests, changes already tried, decisions, assignment) instead of resuming its conversation; the owner chose this on 25 Nov 2026, and it reverses the resume rule.
- New and existing client repos both get these changes on upgrade; no repo setting changes.

## Why

Builder rounds re-send large inputs. Astra's audit measured one build at 46 model requests and about 4.6M input tokens. A resumed repair round starts with a median 170k input tokens, against 56k for a fresh brief. The fresh brief inlines the 25.5 KB standards file, design documents and the test-audit section even for backend work, and large diffs and related-test lists are pasted in full. History undercounts 241 of 750 medium runs, so the baseline comes first.

## Done when

1. **A baseline of input tokens and model requests per build and repair round, by effort, is recorded before any change ships.**
2. **After each change, the same measure on the same kinds of work is recorded and the drop is stated as a measured number.**
3. **A build brief no longer inlines the standards file or the design notes for non-UI work, and names them as files to open.**
4. **Diffs over 2,000 characters and long test lists show file names with a size note, while required tests and failing check names stay inline.**
5. **A repair round starts from a compacted brief instead of resuming a long conversation.**

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
