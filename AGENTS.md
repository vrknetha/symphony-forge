# AGENTS.md — Symphony-Forge

## What This Is

Plan-driven engineering platform. Engineers write 2-page plans, agents build production code.

## Workspace

```
apps/api/          → NestJS backend (Prisma, PostgreSQL)
apps/web/          → React + Vite + Tailwind + TanStack + Zustand
packages/shared/   → Cross-app types, DTOs, constants
linters/           → Structural integrity checks (5 scripts)
scripts/           → boot.sh, setup-worktree.sh, teardown-worktree.sh, generate-api-client.sh
harness/nestjs-react/conventions/  → YOUR RULEBOOK (20 files, ~4000 lines)
projects/          → Per-project plans (PLAN.md = source of truth)
```

## Boot

```bash
./scripts/boot.sh        # docker up + install + migrate + seed + build shared
pnpm dev                 # start API + web in parallel
curl localhost:3000/health  # verify API
```

## Stack (LOCKED)

NestJS + Prisma + PostgreSQL | React + Vite + Tailwind + shadcn + TanStack + Zustand | pnpm + Turborepo | Vitest | GitHub Actions

Auth provider is project-specific (see PLAN.md). Convention defines the contract, not the provider.

## Architecture

Downward-only imports: UI → Runtime → Service → Repository → Config → Types. Enforced by `linters/check-imports.ts`. See `harness/nestjs-react/conventions/architecture.md`.

## Conventions — Read Before Writing Code

| Building... | Read these |
|---|---|
| Any backend module | `code-quality.md`, `api-patterns.md`, `architecture.md` |
| Database / Prisma | `database.md` |
| Auth / guards | `security.md` |
| Tests (MANDATORY) | `testing.md` |
| Logging | `logging.md` |
| Frontend | `frontend-patterns.md` |
| Workers / queues | `workers.md` |
| Git commits | `git.md` |
| CI pipeline | `ci-pipeline.md` |

Full list: `harness/nestjs-react/conventions/` (20 files). Do not skim — read each relevant one fully.

## The One Rule That Gates Everything

**You MUST NOT move to the next module until the current module has 100% test coverage.**

Every service, guard, pipe, interceptor gets a co-located `.spec.ts`. Every entity gets a factory in `apps/api/test/factories/`. No exceptions.

## Build Order

1. Prisma schema + migrations → test factories → test harness
2. Common modules (AppException, correlation middleware, response interceptor) + their specs
3. Auth module + specs → STOP until 100% coverage
4. Domain modules (one at a time) + specs → STOP after each
5. Integration tests (`apps/api/test/*.int-spec.ts`)
6. Frontend pages + component tests

## Common Tasks

| Task | Command |
|---|---|
| Add a domain module | `nest g module <name>`, then service/controller/repository/dto/errors/spec |
| Run migrations | `pnpm db:migrate` |
| Run all checks | `pnpm check:structural` |
| Run tests | `pnpm test` |
| Generate API client | `pnpm generate:api-client` |
| Create worktree | `./scripts/setup-worktree.sh <branch>` |

## What NOT To Do

- **No `any`.** Use `unknown` + type narrowing.
- **No `console.log`.** Use nestjs-pino structured logger.
- **No raw Prisma in responses.** Map to typed DTOs.
- **No cross-domain imports.** Use events or shared interfaces.
- **No tests = not done.** Write specs immediately, not "later."
- **No files over 200 lines.** Split at 150. Controllers max 100.

## Structured Errors

All errors use `AppException` with `{ status, category, code, description, retryable }`. See `code-quality.md`.

## When Conventions Conflict With PLAN.md

- PLAN.md wins for project decisions (auth provider, domain model, features)
- Convention wins for code patterns (file size, testing, logging, errors)
- If ambiguous: `// CONVENTION_CONFLICT: <convention> says X, PLAN says Y, chose Y because Z`

## Where to Look Next

- `harness/nestjs-react/conventions/` — all 20 convention files
- `harness/nestjs-react/SCAFFOLD_PROMPT.md` — full scaffold spec
- `projects/` — project-specific plans (PLAN.md per project)
- `docs/` — getting started, philosophy, validation loop
