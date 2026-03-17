import { fileURLToPath } from 'url';
import { dirname } from 'path';
const ___linterDir = dirname(fileURLToPath(import.meta.url));
/**
 * Structural linter: file size limits.
 * See conventions/code-quality.md
 *
 * Rules:
 *   Source files (.ts/.tsx/.css): max 200 lines, target 150
 *   Controllers: max 100 lines
 *   Excluded: .spec.ts, .e2e-spec.ts, .sql, .json, .prisma, .md, generated/, dist/
 */
import { readdirSync, readFileSync, statSync } from 'fs';
import { join, relative } from 'path';

const HARD_MAX = 200;
const CONTROLLER_MAX = 100;
const EXCLUDE_PATTERNS = [
  /\.spec\.ts$/,
  /\.e2e-spec\.ts$/,
  /\.int-spec\.ts$/,
  /\.sql$/,
  /\.json$/,
  /\.prisma$/,
  /\.md$/,
  /node_modules/,
  /dist\//,
  /coverage\//,
  /generated/,
  /\.turbo/,
];

const SOURCE_EXTENSIONS = ['.ts', '.tsx', '.css'];

interface Violation {
  file: string;
  lines: number;
  max: number;
  rule: string;
  fix: string;
}

function walk(dir: string): string[] {
  const results: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(full));
    } else if (SOURCE_EXTENSIONS.some((ext) => entry.name.endsWith(ext))) {
      results.push(full);
    }
  }
  return results;
}

function check(root: string): Violation[] {
  const violations: Violation[] = [];
  const files = walk(root);

  for (const file of files) {
    const rel = relative(root, file);
    if (EXCLUDE_PATTERNS.some((p) => p.test(rel))) continue;

    const content = readFileSync(file, 'utf-8');
    const lineCount = content.split('\n').length;
    const isController = file.includes('.controller.');
    const max = isController ? CONTROLLER_MAX : HARD_MAX;

    if (lineCount > max) {
      violations.push({
        file: rel,
        lines: lineCount,
        max,
        rule: isController
          ? 'CONTROLLER_TOO_LARGE'
          : 'FILE_TOO_LARGE',
        fix: `Split by responsibility. Each file should have one reason to change. See conventions/code-quality.md`,
      });
    }
  }

  return violations;
}

const root = join(___linterDir, '..');
const violations = check(root);

if (violations.length > 0) {
  console.error(`\n❌ ${violations.length} file size violation(s):\n`);
  for (const v of violations) {
    console.error(
      `  ${v.rule}: ${v.file} is ${v.lines} lines (max ${v.max}). ${v.fix}`,
    );
  }
  process.exit(1);
} else {
  console.log('✅ File size check passed.');
}
