# Convention Audit — Round 1 (Codex gpt-5.4, high reasoning)

**Date:** 2026-03-17
**Input:** AGENTS.md + PLAN.md + 20 convention files (~3965 lines)
**Output:** 57 API files, 5 web files, 1 shared package
**Tokens:** ~211K

## Scorecard

| Convention | Pass/Fail | Notes |
|---|---|---|
| code-quality.md | ⚠️ PARTIAL | 2 files over 150-line target (195, 165). 0 over 200 hard max. Controllers all under 100. Zero `any`, `console.log`, `@ts-ignore`, raw Prisma in responses. |
| code-quality.md (tests) | ❌ FAIL | **Zero test files created.** Convention says 100% coverage, no exceptions. |
| code-quality.md (naming) | ⚠️ PARTIAL | 12 files don't match standard suffixes. Missing: `.constants.ts`, `.mappers.ts`, `.errors.ts`, `.interceptor.ts`, `.types.ts`, `.utils.ts`. Convention only lists 6 suffixes. |
| code-quality.md (deps) | ✅ PASS | All classes ≤5 constructor injections. No circular deps visible. |
| architecture.md | ⚠️ CONFLICT | Convention says Cognito. PLAN says Azure AD. Codex followed PLAN (correct per hierarchy). **Convention needs updating.** |
| api-patterns.md | TODO | Need deeper review |
| database.md | TODO | Need to check Prisma schema, migrations |
| design-patterns.md | TODO | Repository pattern used correctly |
| frontend-patterns.md | ❌ N/A | Web app barely scaffolded by PTY session |
| testing.md | ❌ FAIL | Zero tests. Convention not followed at all. |
| ci-pipeline.md | ❌ FAIL | No CI config created. |
| workers.md | ❌ N/A | No workers needed for v1 |
| logging.md | ❌ FAIL | No structured logger. Uses NestJS default. |
| security.md | TODO | Need to check auth guards, rate limiting |
| git.md | ✅ PASS | Meaningful commit messages, proper branching |
| linters.md | ❌ FAIL | No ESLint/Prettier config in API |
| worktree-lifecycle.md | ❌ N/A | Not applicable to scaffold |
| core-beliefs.md | ✅ PASS | Repository pattern, DTOs, structured errors |
| quality-grades.md | TODO | Need to grade output |
| plans.md | ✅ PASS | Created execution plan, updated progress |
| agent-review.md | ❌ N/A | No self-review performed |
| agent-observability.md | ❌ FAIL | No observability setup |
| doc-gardening.md | ❌ N/A | Not applicable |

## Critical Gaps Found

### 1. NO TEST GUIDANCE FOR AGENTS
Convention says "100% coverage" but gives zero examples of what a NestJS service test looks like with mocked repos. Agent skipped entirely. **Convention needs: concrete test file example, mock patterns, factory setup.**

### 2. NAMING CONVENTION INCOMPLETE
Only lists 6 suffixes (`.service.ts`, `.controller.ts`, `.repository.ts`, `.dto.ts`, `.guard.ts`, `.filter.ts`). Codex needed: `.constants.ts`, `.mappers.ts`, `.errors.ts`, `.interceptor.ts`, `.types.ts`, `.utils.ts`, `.strategy.ts`, `.client.ts`, `.config.ts`, `.pipe.ts`. **Convention needs: complete suffix list.**

### 3. NO ERROR HANDLING EXAMPLES
Codex invented its own `AppException` pattern (actually decent). Convention says "Throw NestJS exceptions, never manual error objects" — but Codex correctly identified that NestJS built-in exceptions lack `category`/`retryable`/`description` fields that AGENTS.md requires. **Convention contradicts AGENTS.md. Needs reconciliation with example.**

### 4. NO LOGGING SETUP GUIDANCE
Convention exists but has no "here's how to set up structured logging in NestJS" example. Agent ignored it completely.

### 5. SCAFFOLD_PROMPT.md SHOWS 80%/70%/60% COVERAGE
Directly contradicts code-quality.md's 100% rule. **Delete the percentages from SCAFFOLD_PROMPT.md.**

### 6. NO LINTER/PRETTIER BOOTSTRAP
Convention exists but no starter configs. Agent didn't create them.

### 7. ARCHITECTURE.MD SAYS COGNITO, PLAN SAYS AZURE AD
Convention needs to be auth-agnostic or parameterized. Currently it prescribes a specific provider.

### 8. NO FILE SPLIT GUIDANCE
Two files at 195 and 165 lines. Convention says target=150, max=200. But no guidance on HOW to split when approaching the limit. **Need: "when a service crosses 150 lines, extract domain-specific sub-services" with example.**

## What Codex Did Well (Convention Worked)
- Repository pattern separation (every module has repo + service + controller)
- DTOs for all inputs/outputs (no raw Prisma leakage)
- Structured error pattern (invented a good one despite weak guidance)
- Clean module organization (auth, projects, documents, agent-keys)
- Proper NestJS decorators and Swagger annotations
- Slug generation utility extracted correctly
- Constructor injection kept lean

## Improvements for Round 2

1. Add complete file suffix list to code-quality.md
2. Add test file example (service + repo mock) to testing.md
3. Add structured logging bootstrap to logging.md
4. Add ESLint + Prettier starter config to linters.md
5. Fix SCAFFOLD_PROMPT.md coverage percentages → 100%
6. Make architecture.md auth-agnostic (parameterized)
7. Add AppException/structured error example to code-quality.md
8. Add "how to split a 150+ line file" guide with before/after
9. Add CI config example to ci-pipeline.md
