---
status: accepted
confirmed_by: "vrknetha"
date: 2026-07-24
---

# Project-Level Memory

## Context
Agent session memory defaulted to the personal store (`~/.claude/.../memory`),
so project knowledge accumulated per-machine and per-person: a teammate
cloning the repo inherited none of it. Directed by the maintainer in-session
(2026-07-24).

## Decision
Durable project knowledge is recorded at PROJECT level, in-repo: decision
records for choices, `docs/context/` for narrative context, `.gstack/` for
gstack-produced history. The personal `~/.claude` memory store is not used
for project facts.

## Consequences
Every clone inherits the project's memory; nothing load-bearing lives on one
person's machine. Personal stores may still hold cross-project user
preferences — never project state. `.claude/CLAUDE.md` ground rules updated.
