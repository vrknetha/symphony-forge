---
status: accepted
confirmed_by: "vrknetha"
date: 2026-07-24
---

# Client Signoff

## Context
The harness repo itself had no recorded sign-off, so its own gate chain
(intake → sign-off → plan save) blocked harness maintenance work. First
blocked task: FORGE-INIT-1, fixing `forge init`'s blanket non-empty-target
refusal (hit while bootstrapping the agentstats repo, 2026-07-24).

## Decision
The harness maintainer (repo owner) is the client for symphony-forge itself;
their approval of a task's plan constitutes sign-off for harness maintenance
runs.

## Consequences
Harness fixes flow through the same factory gates as client work — intake,
saved plan, verify, autoreview evidence — with the maintainer's plan
approval standing in for client sign-off. No gate is bypassed.
