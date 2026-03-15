# Testing Conventions

## Pyramid

- **Unit (Vitest):** Co-located `*.spec.ts`, mock Prisma, cover services/utils/repos
- **Integration (Supertest):** `apps/api/test/*.e2e-spec.ts`, real DB, full HTTP cycle
- **E2E (Playwright):** `apps/web/e2e/`, critical user journeys only (thin layer)
- **Structural (custom linters):** `pnpm check:all`, blocks merge on violation

## Coverage Targets

| Layer | Target |
|-------|--------|
| Services | ≥ 80% |
| Repositories | ≥ 70% |
| Controllers | ≥ 60% |
| Utils | ≥ 90% |

## Rules

- Use factories with faker for test data. Never hardcode.
- Each test file owns its data. No shared fixtures.
- No `.skip` or `xit` without a tracked issue.
- Integration tests need `TEST_DATABASE_URL` env var.
