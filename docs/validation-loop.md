# Validation Loop

The validation loop is the process by which Symphony (and human developers) confirm that a completed slice of work is genuinely production-ready — not just "it compiles."

Each iteration of the loop covers four phases. A slice is not done until all four pass.

---

## Phase 1: Structural Integrity

**Goal:** Confirm the code respects the architecture.

Run:
```bash
pnpm check:all
```

This executes three linters in sequence:

| Linter | What it checks |
|--------|----------------|
| `check-imports.ts` | Layer dependency direction (Types → Config → Repo → Service → Runtime → UI) |
| `check-boundaries.ts` | No direct cross-domain imports |
| `check-docs.ts` | AGENTS.md references exist, docs are fresh, cross-links resolve |

**A slice fails Phase 1 if any linter exits non-zero.** The error messages include:
- The exact file with the violation
- What it illegally imports
- Which architecture rule was broken
- A link to the relevant doc section

**Why this matters before tests:** Structural violations often mean the wrong abstraction was chosen. Running tests before catching this wastes time debugging the wrong code.

---

## Phase 2: Type Safety

**Goal:** No TypeScript errors anywhere in the monorepo.

Run:
```bash
pnpm turbo run typecheck
```

This runs `tsc --noEmit` across all packages in dependency order (shared → api, shared → web).

**Common failure patterns:**
- Missing return type annotation on a public service method
- DTO shape mismatch between API response and shared type
- Generated API client out of sync (run `pnpm generate:api-client` to fix)

**Fix the root cause, not the symptom.** Using `as any` or `@ts-ignore` to silence a type error is a Phase 2 failure even if `tsc` exits 0.

---

## Phase 3: Tests

**Goal:** All unit and integration tests pass.

Run:
```bash
pnpm turbo run test
```

Test coverage requirements (enforced in CI):
- **Services:** ≥ 80% line coverage
- **Repositories:** ≥ 70% line coverage
- **Controllers:** ≥ 60% line coverage (thin wrappers — logic belongs in services)

**Integration tests** (`*.e2e.spec.ts`) run against a real Postgres instance. They must pass in CI (Docker service is provided) and locally (via `./scripts/boot.sh`).

**What "tests pass" actually means:**
1. All assertions green
2. No tests skipped with `.skip` or `xit` that weren't skipped before this slice
3. No new `console.error` output in test runs (indicates unhandled errors)

---

## Phase 4: Vertical Slice Smoke Test

**Goal:** The feature works end-to-end, as a user would experience it.

This is a manual or automated check that exercises the full slice:
`HTTP request → NestJS controller → service → repository → DB → response → React UI`

**Checklist:**
- [ ] The API endpoint returns the expected response (curl or Swagger UI)
- [ ] Error cases return the correct HTTP status and error shape
- [ ] The React UI renders the data correctly
- [ ] Authentication/authorization is enforced (test with and without a valid token)
- [ ] The feature behaves correctly after a page refresh (no state hydration issues)
- [ ] No unhandled promise rejections in the browser console
- [ ] No N+1 queries (check Prisma query logs in development)

**For agent-driven work:** The agent must document the smoke test result in the PR description, including:
- The exact curl command (or Playwright test) used to verify the happy path
- The error case that was tested
- Any edge case that was intentionally deferred (with a filed issue)

---

## Loop Cadence

```
┌─────────────────────────────────────────────────────┐
│  Implement vertical slice (one domain endpoint)     │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
              Phase 1: pnpm check:all
                        │
              ┌─────────┴──────────┐
           FAIL                  PASS
              │                   │
         Fix arch            Phase 2: tsc
         violation                │
              │          ┌────────┴────────┐
              │       FAIL              PASS
              │          │                │
              └──────────┘        Phase 3: pnpm test
                                          │
                                 ┌────────┴────────┐
                                FAIL             PASS
                                 │                │
                            Fix tests       Phase 4: smoke
                                 │                │
                                 │       ┌────────┴────────┐
                                 │    FAIL             PASS
                                 │       │                │
                                 └───────┘           ✅ Done
```

---

## Automating the Loop (Symphony Integration)

When Symphony is configured (see `docs/symphony-setup.md`), it runs the validation loop automatically after each agent commit:

1. **Webhook fires** on push to the worktree branch
2. Symphony runs `pnpm check:all && pnpm turbo run typecheck && pnpm turbo run test`
3. If any phase fails, Symphony posts a structured error report back to the agent
4. The agent reads the error, applies the fix, and pushes again
5. The loop repeats until all phases pass
6. Symphony merges the branch and marks the Linear issue Done

The error messages from the linters are deliberately agent-readable — they tell you exactly what to fix and where.

For local factory sessions, the equivalent one-command gate is:

```bash
python3 .codex/scripts/validate_work.py
```

It runs deterministic verify, validates `.factory` testing/review artifacts, and marks the run PR-ready only when all gates pass.
