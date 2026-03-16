# Plan: Scaffold Symphony-Forge v1 projects and documents platform

**Status:** In Progress
**Branch:** main
**Created:** 2026-03-16
**Last updated:** 2026-03-16

## Context

The repo currently contains the v1 product plan and conventions, but not the actual monorepo scaffold. This work creates the pnpm/turbo workspace, NestJS API, React web app, and shared package needed for Projects + Documents with Azure AD auth and Proof SDK integration.

## Approach

1. Initialize the monorepo root with workspace wiring, shared scripts, and baseline docs.
2. Scaffold the NestJS API with config, Prisma schema, structured errors, and the auth, projects, documents, and agent-keys modules.
3. Scaffold the React web app with Vite, Tailwind, routing, guards, and page shells for the required flows.
4. Add the shared package for types, enums, document templates, and API DTO contracts.
5. Install dependencies, run verification commands, update docs/plan state, and commit each user-requested step separately.

## Progress

- [x] Create execution plan
- [x] Initialize monorepo root files
- [x] Scaffold API application
- [ ] Scaffold web application
- [ ] Add shared package
- [ ] Run verification and final notification command

## Decision Log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2026-03-16 | Prefer the product plan over conflicting auth conventions | `PLAN.md` requires Azure AD OIDC, while `architecture.md` mentions Cognito. The convention hierarchy says plans override docs. |
| 2026-03-16 | Use a plan-aligned structured error envelope with additional metadata | The conventions disagree on error shape, and `AGENTS.md` requires `category`, `retryable`, and `description`. The API scaffold will standardize on one response shape that satisfies the hard rule. |

## Risks / Open Questions

- Proof SDK package names and embedding surface may require adjustment if the published package layout differs from the plan assumptions. Status: open.
- Full 100% line coverage is unlikely to be reached in a single scaffold pass without significant follow-up test work. Status: open.

## Completion Criteria

- [ ] Monorepo root files created and wired through pnpm + turbo
- [ ] API scaffold compiles with Prisma schema and required modules
- [ ] Web scaffold compiles with routing and auth wiring
- [ ] Shared package exports the common contracts used by both apps
- [ ] Verification commands run and results recorded
- [ ] Final notification command executed
