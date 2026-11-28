# Shorten reviews and carry plan requirements through to close

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Builders see the checks they owe in their briefs, and reviewers verify those same checks at close.
- Owners get fewer repeated review rounds and named follow-ups for ordinary findings that remain open.

## Why

Forge can hold a plan on a scored advisory, run repeated full code reviews, and tell a reviewer that a read note was accepted even when the builder was expected to act on it.

## Done when

1. **Each read-note decision records either “accepted risk” or “builder must prove”; the latter names the affected part and an observable check, appears in the builder brief and both review templates, and is verified at close.**
2. **Pinned Autoreview runs one pass per code review round, with one full review for a fix and at most two rounds for a story part. Round two checks earlier findings and admits only new P0 defects that affect normal use.**
3. **At the round limit, ordinary leftovers become named follow-ups. An open P0 or unmet owner-approved requirement stops for the owner.**
4. **Reads and code use the same Gain, Work and Harm scores. Advisory notes never hold a read, Gain 3 and Harm 3 alone cannot hold it, and from round two only Harm 4 or 5 or a still-open earlier blocker can hold it. The code review threshold stays as it is.**
5. **Each code reviewer comes from a different model family than the builder. Terra Max reviews Claude and Antigravity work, and Claude must pass the recorded cases before reviewing Codex work. The first cold reader comes from a different family than the plan author and stays for repairs.**
6. **New repos get these rules at setup, and existing repos get them on upgrade with their recorded owner decisions and open stops preserved.**

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
