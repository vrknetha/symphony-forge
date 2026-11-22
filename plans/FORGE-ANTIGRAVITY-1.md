# Google Antigravity as a third coding agent

<n> parts · Risks: ... · New moving parts: ...

## What changes for you

- Owners can pick Google Antigravity (Gemini 4 Neon) as a third coding agent next to Claude Code and Codex.
- Each job (build, fix, review, cold read) can run on any of the three agents, set in forge.toml with a model and effort per job type, with the same effort ladder, shared agent lanes, run records, cost and skills as the other two.
- A repair round continues the same Antigravity session, as it does for Claude and Codex.
- Forge refuses a review done by the same agent family that built the change. Current defaults stay the same.
- Antigravity connects through Google's official agent over the Agent Client Protocol (a standard way for a tool to talk to a coding agent). It needs Antigravity 1.5 or newer.
- Any Google sign-in works, a personal Google account by default. Doctor warns that Google's terms for outside tools are unclear and names an API key and Vertex AI (Google's cloud AI service) as other options.

## Why

Forge runs only Claude and Codex today, so a team that wants Google's agent cannot use Forge's build, review and merge flow with it.

## Done when

1. **A repo whose forge.toml names Antigravity for building runs its builds on Antigravity, and close shows the run as Antigravity with its model, effort and cost.**
2. **A repair round on an Antigravity build continues the same Antigravity session instead of starting a fresh one.**
3. **A review or cold read set to Antigravity runs on it, and a review by the builder's own family is refused with a plain message.**
4. **Antigravity runs wait for a place in the shared agent lanes like Claude and Codex runs.**
5. **Doctor says whether Antigravity is installed, signed in and at version 1.5 or newer, and shows the terms warning.**
6. **A new repo can choose Antigravity at init, and an existing repo keeps its Claude and Codex settings unchanged after upgrade.**

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
