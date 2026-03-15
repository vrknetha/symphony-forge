# Structural Linter Conventions

Three custom linters run via `pnpm check:all`. All must pass before merge.

## check-imports.ts
- Walks `apps/api/src/`
- Detects layer by file naming: `.dto.ts`/`.type.ts` = Types, `.repository.ts` = Repo, `.service.ts` = Service, `.controller.ts`/`.guard.ts` = Runtime, `.module.ts` = Runtime, `.config.ts` = Config
- Flags any import from a higher layer
- Error format: file, illegal import, rule broken, fix instruction, doc link

## check-boundaries.ts
- Detects cross-domain imports (module A importing module B internals)
- Same error message quality as check-imports

## check-docs.ts
- Validates every file path referenced in AGENTS.md exists
- Flags stale references and broken links

## Error Message Quality (Non-Negotiable)

Every violation message must include:
1. Exact file path
2. What was illegally imported
3. Which rule was broken
4. What to do instead
5. Link to relevant doc

These messages ARE the remediation. An agent reading them should fix the issue without additional context.
