# Audit: Round 2 — Convention Compliance

**Date:** 2026-03-17
**Agent:** Codex (gpt-5.4, --full-auto, reasoning:high)
**Input:** AGENTS.md v2 + 20 convention files + PLAN.md

## Scorecard

| Convention | Round 1 | Round 2 | Verdict |
|---|---|---|---|
| AppException (structured errors) | ❌ None | ✅ Full | **FIXED** |
| Structured logging (nestjs-pino) | ❌ None | ✅ Full + correlation IDs | **FIXED** |
| File sizes ≤200 lines | ⚠️ 3 violations | ✅ Max 134 lines | **FIXED** |
| No console.log | ❌ Some | ✅ Zero | **FIXED** |
| No `any` | ❌ Some | ✅ Zero | **FIXED** |
| Domain error modules (*.errors.ts) | ❌ None | ✅ 4 modules | **FIXED** |
| Naming suffixes | ⚠️ 12 non-standard | ✅ All standard (18 suffixes) | **FIXED** |
| Encryption (ownerSecret) | ❌ None | ✅ encryption.service.ts | **FIXED** |
| DTOs (input + output) | ⚠️ Missing outputs | ✅ Full request + response DTOs | **FIXED** |
| Proof proxy module | ❌ None | ✅ proof-proxy module | **NEW** |
| **Unit tests** | **❌ Zero** | **❌ Zero** | **NOT FIXED** |
| **Test factories** | **❌ None** | **❌ None** | **NOT FIXED** |
| **Test harness** | **❌ None** | **❌ None** | **NOT FIXED** |
| CI pipeline config | ❌ None | ❌ None | NOT FIXED |
| Structural linters | ❌ None | ❌ None | NOT FIXED |

## Summary

- **7 of 9 code conventions now passing** (was 0 in Round 1)
- **Testing remains the critical gap** — 0 spec files across 70 source files
- AGENTS.md v2 checklist was read but testing steps were skipped

## Files Generated

| Category | Count | Round 1 |
|---|---|---|
| Source (.ts, no spec) | 70 | 57 |
| Spec files | 0 | 0 |
| Factories | 0 | 0 |
| Modules (domains) | 7 | 5 |

## Root Cause Analysis

Codex read all 10 convention files before building (confirmed). It followed code-quality and logging conventions perfectly. But the "write tests after each module" instruction in Build Order was ignored — Codex built all modules sequentially without pausing for tests.

**Hypothesis:** Codex optimizes for "build the thing" and treats test instructions as lower priority. The Build Order section was too implicit — it said "write tests" but didn't gate progression on test existence.

## Fix Applied for Round 3

AGENTS.md v3 changes:
1. Added `⛔ THE ONE RULE THAT GATES EVERYTHING` section — tests must exist before next module
2. Build Order now has explicit `STOP. Do not start Phase N until tests exist.` gates
3. Inlined test patterns directly in AGENTS.md (unit test + factory + mock strategy)
4. Per-module checklist expanded with bold test requirements
5. Test writing moved from Hard Rule #6 to Hard Rule #1

## Convention Changes for Round 3

None needed — testing.md and code-quality.md are comprehensive. The gap was in AGENTS.md not enforcing the gate strongly enough.
