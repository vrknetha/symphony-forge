ROUND 2 BUILD — Convention-Compliant Scaffold

YOU MUST READ THESE FILES FIRST (in order):
1. AGENTS.md (your rules and compliance checklist)
2. projects/knack-forge/PLAN.md (what to build)
3. harness/nestjs-react/conventions/code-quality.md
4. harness/nestjs-react/conventions/testing.md
5. harness/nestjs-react/conventions/logging.md
6. harness/nestjs-react/conventions/api-patterns.md
7. harness/nestjs-react/conventions/architecture.md
8. harness/nestjs-react/conventions/database.md
9. harness/nestjs-react/conventions/security.md
10. harness/nestjs-react/conventions/frontend-patterns.md

CRITICAL REQUIREMENTS (Round 1 failed on these):
- 100% test coverage: Every service, guard, pipe gets co-located *.spec.ts
- Structured logging: nestjs-pino with correlation IDs per logging.md
- AppException errors: category/code/description/retryable per code-quality.md
- File size: every source file ≤200 lines (target 150, split if >150)
- Complete file suffixes per code-quality.md naming table
- Zero any, console.log, @ts-ignore, magic numbers
- Factories in test/factories/ using faker

Build: monorepo root -> API (auth + projects + documents + agent-keys) -> shared types -> web dashboard -> tests -> logging -> CI config.

After EACH module, run the compliance checklist from AGENTS.md before moving to the next.
