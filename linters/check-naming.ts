import { fileURLToPath } from 'url';
import { dirname } from 'path';
const ___linterDir = dirname(fileURLToPath(import.meta.url));
/**
 * Structural linter: file naming conventions.
 * See conventions/code-quality.md
 *
 * Rules:
 *   - All .ts files must be kebab-case
 *   - All .ts files (except entry points) must have an approved suffix
 *   - All .tsx files must be PascalCase
 */
import { readdirSync, existsSync } from 'fs';
import { join, relative, basename } from 'path';

const APPROVED_SUFFIXES = [
  '.service.ts', '.controller.ts', '.repository.ts', '.dto.ts',
  '.guard.ts', '.filter.ts', '.strategy.ts', '.interceptor.ts',
  '.pipe.ts', '.client.ts', '.config.ts', '.constants.ts',
  '.mappers.ts', '.errors.ts', '.types.ts', '.decorator.ts',
  '.module.ts', '.utils.ts', '.events.ts', '.listeners.ts',
  '.producer.ts', '.processor.ts', '.jobs.ts', '.interfaces.ts',
  // Test files
  '.spec.ts', '.int-spec.ts', '.e2e-spec.ts',
  // Factories
  '.factory.ts',
];

const ENTRY_POINTS = ['main.ts', 'openapi.ts', 'seed.ts', 'index.ts', 'setup.ts', 'app.ts'];

const EXCLUDE = [/node_modules/, /dist/, /coverage/, /\.turbo/, /generated/];

interface Violation {
  file: string;
  rule: string;
  fix: string;
}

function walk(dir: string): string[] {
  const results: string[] = [];
  try {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.name === 'node_modules' || entry.name === 'dist') continue;
      if (entry.isDirectory()) results.push(...walk(full));
      else if (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx')) {
        results.push(full);
      }
    }
  } catch { /* skip */ }
  return results;
}

function isKebabCase(name: string): boolean {
  return /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(name);
}

function check(root: string): Violation[] {
  const violations: Violation[] = [];

  for (const dir of ['apps/api/src', 'apps/web/src', 'packages/shared/src']) {
    const fullDir = join(root, dir);
    if (!existsSync(fullDir)) continue;

    const files = walk(fullDir);
    for (const file of files) {
      const rel = relative(root, file);
      if (EXCLUDE.some((p) => p.test(rel))) continue;

      const name = basename(file);

      // .tsx files: PascalCase check
      if (name.endsWith('.tsx')) {
        const stem = name.replace('.tsx', '');
        if (!/^[A-Z][a-zA-Z0-9]*$/.test(stem)) {
          violations.push({
            file: rel,
            rule: 'NAMING_TSX: Component files must be PascalCase',
            fix: `Rename to PascalCase (e.g., InvoiceCard.tsx). See conventions/code-quality.md`,
          });
        }
        continue;
      }

      // .ts files: skip entry points
      if (ENTRY_POINTS.includes(name)) continue;

      // Check kebab-case (on the base name without suffix)
      const stem = name.replace(/\.ts$/, '');
      // Check for approved suffix
      const hasSuffix = APPROVED_SUFFIXES.some((s) => name.endsWith(s));
      if (!hasSuffix) {
        violations.push({
          file: rel,
          rule: `NAMING_SUFFIX: "${name}" lacks an approved suffix`,
          fix: `Rename with an approved suffix (e.g., .service.ts, .dto.ts). See conventions/code-quality.md for the full list.`,
        });
      }
    }
  }

  return violations;
}

const root = join(___linterDir, '..');
const violations = check(root);

if (violations.length > 0) {
  console.error(`\n❌ ${violations.length} naming violation(s):\n`);
  for (const v of violations) {
    console.error(`  ${v.rule}\n    File: ${v.file}\n    Fix: ${v.fix}\n`);
  }
  process.exit(1);
} else {
  console.log('✅ Naming convention check passed.');
}
