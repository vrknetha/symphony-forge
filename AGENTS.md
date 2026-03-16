# AGENTS.md — Symphony-Forge

## Workspace: /private/tmp/symphony-forge

## What This Is

Plan-driven engineering platform for KnackLabs. Engineers write plans, agents build production code.

## Current Task

Build the v1 platform: Projects + Documents with Azure AD auth and Proof SDK integration.
**Read `projects/knack-forge/PLAN.md` before writing any code.** That is the source of truth.

## Stack (LOCKED)

- **API:** NestJS + Prisma + PostgreSQL
- **Web:** React + Vite + Tailwind + TanStack Query + Zustand
- **Editor:** Proof SDK (collaborative markdown — install as npm dependency, DO NOT fork)
- **Auth:** Azure AD / Entra ID OIDC
- **Build:** pnpm + Turborepo
- **Testing:** Vitest (API + Web), 100% line coverage target

## Repo Structure

```
symphony-forge/
├── apps/
│   ├── web/                    # React + Vite + Tailwind
│   └── api/                    # NestJS backend
├── packages/
│   └── shared/                 # Types, DTOs, constants
├── harness/
│   └── nestjs-react/           # Convention files (READ THESE)
│       ├── SCAFFOLD_PROMPT.md
│       └── conventions/*.md
├── projects/
│   └── knack-forge/            # This project's plan
│       └── PLAN.md
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

## Convention System

All conventions live in `harness/nestjs-react/conventions/*.md`. 
**Read ALL relevant conventions before writing code for any module.**

Key conventions for this project:
- `architecture.md` — modular monolith, domain boundaries
- `api-patterns.md` — REST conventions, error shapes, pagination
- `code-quality.md` — 200-line max, zero tolerance rules
- `database.md` — Prisma patterns, migrations, seeding
- `frontend-patterns.md` — component rules, state management, Tailwind-only
- `testing.md` — coverage requirements, factory patterns
- `security.md` — auth, input validation, secrets handling

## Hard Rules

1. **100% line coverage.** No exceptions.
2. **200-line max per source file** (excl. tests, .sql, .json, .prisma, .md, generated).
3. **Every API error:** structured with category + retryable + description.
4. **Every mutation:** idempotency handling where applicable.
5. **Zero tolerance:** `any`, `console.log` in prod, `@ts-ignore` without issue, magic numbers, commented-out code.
6. **Proof SDK is a dependency.** Do NOT modify its source. Use its HTTP API.
7. **Proof ownerSecret must be encrypted at rest** in PostgreSQL.

## Build Order

Follow PLAN.md phases:
1. Init monorepo (pnpm + Turborepo)
2. Scaffold NestJS API with auth module
3. Scaffold React dashboard with login
4. Project CRUD
5. Document CRUD + Proof SDK integration
6. Proof SDK editor embed in frontend

## When Conventions Conflict With the Plan

- Raise it explicitly. Quote both sources. Propose resolution.
- Don't silently pick one. Comment in the code with `// CONVENTION_CONFLICT: ...`

## When You're Stuck

- Re-read the relevant convention file
- If convention doesn't cover it, make the pragmatic choice and document WHY
- Prefer boring, correct code over clever code
