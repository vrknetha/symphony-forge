# Testing Conventions

## Pyramid

| Layer | Tool | Location | Scope |
|-------|------|----------|-------|
| Unit | Vitest | `*.spec.ts` (co-located) | Pure logic, zero I/O |
| Integration | Vitest + Supertest | `apps/api/test/*.int-spec.ts` | Full HTTP path, real DB |
| E2E | Playwright | `apps/web/e2e/` | Critical user journeys only |
| Structural | Custom linters | `pnpm check:all` | File size, imports, naming |

## Coverage

**100% line coverage. No exceptions.** The coverage report IS the todo list.

| Layer | Target | Notes |
|-------|--------|-------|
| Services | 100% | Business logic + every error path |
| Guards | 100% | Allow and deny cases |
| Pipes / Interceptors | 100% | Transform/reject, wrap/modify |
| Controllers | Skip unit tests | Thin wrappers — integration tests cover them |
| Utils | 100% | Pure functions, easiest to test |

---

## Unit Tests

### Isolation

No database. No network. No filesystem. No `setTimeout`. Pure logic only. If it needs I/O, it's an integration test.

### Mock Strategy

Mock the layer directly below. **Never mock two layers deep.**

| Class Under Test | Mocks |
|-----------------|-------|
| Service | Repository |
| Guard | Reflector, ExecutionContext |
| Pipe | — (pure transform) |
| Interceptor | ExecutionContext, CallHandler |

### Test Factories

Use `@faker-js/faker`. Never hardcode. Factories live in `apps/api/test/factories/`.

```typescript
// apps/api/test/factories/user.factory.ts
import { faker } from '@faker-js/faker';
import { User } from '@prisma/client';

export function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: faker.string.uuid(), email: faker.internet.email(),
    name: faker.person.fullName(), role: 'member',
    workspaceId: faker.string.uuid(),
    createdAt: faker.date.recent(), updatedAt: faker.date.recent(),
    ...overrides,
  };
}
```

### Unit Test Pattern

```typescript
// billing/invoice.service.spec.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { InvoiceService } from './invoice.service';
import { InvoiceRepository } from './invoice.repository';
import { buildInvoice } from '../../test/factories/invoice.factory';

describe('InvoiceService', () => {
  let service: InvoiceService;
  let repo: { findById: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    repo = { findById: vi.fn() };
    service = new InvoiceService(repo as unknown as InvoiceRepository);
  });

  it('returns invoice by id', async () => {
    const invoice = buildInvoice();
    repo.findById.mockResolvedValue(invoice);
    expect(await service.getById(invoice.id)).toEqual(invoice);
  });

  it('throws NotFoundException when missing', async () => {
    repo.findById.mockResolvedValue(null);
    await expect(service.getById('x')).rejects.toThrow(NotFoundException);
  });
});
```

### What to Test Per Layer

| Layer | Test These |
|-------|-----------|
| Service | Happy path, every error branch, edge cases (empty arrays, nulls), business rules |
| Guard | `true` for valid claims, `false`/throws for invalid, respects `@Public()` |
| Pipe | Transforms valid input, throws `BadRequestException` on invalid |
| Interceptor | Wraps response shape, modifies headers, handles `next.handle()` errors |

---

## Integration Tests

Each test gets **real Postgres** (worktree's isolated DB) and **real Redis**. No mocks at infrastructure level.

### Transaction Rollback Per Test

Every test runs inside a transaction that rolls back. Faster than truncate, no ordering issues.

```typescript
// apps/api/test/support/test-harness.ts
import { Test } from '@nestjs/testing';
import { PrismaService } from '../../src/prisma/prisma.service';
import { AppModule } from '../../src/app.module';

export async function createTestApp() {
  const mod = await Test.createTestingModule({ imports: [AppModule] }).compile();
  const app = mod.createNestApplication();
  await app.init();
  return app;
}

export function withTransaction(app) {
  const prisma = app.get(PrismaService);
  return {
    async run(fn) {
      await prisma.$transaction(async (tx) => {
        Object.assign(prisma, tx);
        try { await fn(prisma); } finally { throw new Error('ROLLBACK'); }
      }).catch((e) => { if (e.message !== 'ROLLBACK') throw e; });
    },
  };
}
```

### Mock JWT Injection

Inject mock JWTs with known claims. Never use real auth flows in tests.

```typescript
// apps/api/test/support/auth.helper.ts
import * as jwt from 'jsonwebtoken';
const TEST_SECRET = 'test-jwt-secret'; // Must match test env JWT_SECRET

export function mockJwt(claims: Record<string, unknown> = {}) {
  return jwt.sign(
    { sub: 'user-123', email: 'test@test.com', role: 'member', ...claims },
    TEST_SECRET, { expiresIn: '1h' },
  );
}

export const authHeader = (c?) => ({ Authorization: `Bearer ${mockJwt(c)}` });
```

### Integration Test Pattern

```typescript
// apps/api/test/invoice.int-spec.ts
import supertest from 'supertest';
import { createTestApp, withTransaction } from './support/test-harness';
import { authHeader } from './support/auth.helper';

describe('POST /api/v1/invoices', () => {
  let app, tx;
  beforeAll(async () => { app = await createTestApp(); tx = withTransaction(app); });
  afterAll(() => app.close());

  it('creates invoice for authed user', () => tx.run(async () => {
    const res = await supertest(app.getHttpServer())
      .post('/api/v1/invoices').set(authHeader({ role: 'admin' }))
      .send({ amount: 5000, currency: 'USD' }).expect(201);
    expect(res.body).toMatchObject({ amount: 5000 });
  }));

  it('rejects unauthenticated', async () => {
    await supertest(app.getHttpServer()).post('/api/v1/invoices').send({}).expect(401);
  });
});
```

### Execution Model

| Scope | Execution |
|-------|-----------|
| Files | Parallel (Vitest default) |
| Tests within a file | Sequential |
| Data setup | Each `describe` creates its own data via factories |
| Cleanup | Transaction rollback — automatic |

### Test Isolation Checklist

- ✅ Each `describe` block creates its own data — no shared fixtures
- ✅ No reliance on seed data or execution order
- ❌ Never share database rows across `describe` blocks

---

## E2E Tests (Playwright)

Critical user journeys only. **Thin layer** — don't duplicate what integration tests cover.

| ✅ Do test | ❌ Don't test |
|-----------|--------------|
| Login → create → verify in list → delete | Every form validation message |
| Error state renders after failed API call | Individual component behavior |

### Page Object Model

```typescript
// apps/web/e2e/pages/invoice.page.ts
export class InvoicePage {
  constructor(private page: Page) {}
  get createBtn() { return this.page.getByRole('button', { name: 'Create Invoice' }); }
  async create(amount: number) {
    await this.createBtn.click();
    await this.page.getByLabel('Amount').fill(String(amount));
    await this.page.getByRole('button', { name: 'Submit' }).click();
  }
}
```

Visual regression: `toHaveScreenshot()` for layout-critical pages. Snapshots in `apps/web/e2e/__snapshots__/`.

---

## Structural Tests

Run via `pnpm check:all`. Block merge on any violation.

| Check | Script | Catches |
|-------|--------|---------|
| File size | `check-file-size.ts` | Source files over 200 lines |
| Import boundaries | `check-boundaries.ts` | Cross-domain imports, upward deps |
| Naming | `check-naming.ts` | Wrong suffixes, non-kebab filenames |

---

## Rules (Non-Negotiable)

| Rule | Rationale |
|------|-----------|
| No `.skip` / `xit` without linked issue | Dead tests rot silently |
| Factories with faker, never hardcoded | Hardcoded data hides bugs |
| Each test file owns its data | Shared fixtures create coupling |
| `TEST_DATABASE_URL` required for integration | Never hit dev/prod databases |
| No `sleep()` / `setTimeout` in tests | Flaky tests are worse than no tests |
| 100% line coverage, no exceptions | The coverage report IS the todo list |
