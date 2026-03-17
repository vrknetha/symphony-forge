import { fileURLToPath } from 'url';
import { dirname } from 'path';
const ___linterDir = dirname(fileURLToPath(import.meta.url));
/**
 * Structural linter: AGENTS.md reference validation.
 * See conventions/linters.md
 *
 * Validates that every file path referenced in AGENTS.md actually exists.
 */
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

interface Violation {
  path: string;
  line: number;
  rule: string;
  fix: string;
}

function check(root: string): Violation[] {
  const violations: Violation[] = [];
  const agentsPath = join(root, 'AGENTS.md');

  if (!existsSync(agentsPath)) {
    console.log('⚠ AGENTS.md not found — skipping doc check.');
    return [];
  }

  const content = readFileSync(agentsPath, 'utf-8');
  const lines = content.split('\n');

  // Match file paths in backticks or plain references
  const pathRegex = /[`"']?((?:apps|packages|linters|scripts|harness|docs|projects)\/[^\s`"',)]+)[`"']?/g;

  for (let i = 0; i < lines.length; i++) {
    let match: RegExpExecArray | null;
    pathRegex.lastIndex = 0;

    while ((match = pathRegex.exec(lines[i])) !== null) {
      const refPath = match[1].replace(/[`'"]/g, '');
      // Skip glob patterns
      if (refPath.includes('*')) continue;
      // Skip URLs
      if (refPath.includes('://')) continue;

      const fullPath = join(root, refPath);
      if (!existsSync(fullPath)) {
        violations.push({
          path: refPath,
          line: i + 1,
          rule: `STALE_REF: "${refPath}" referenced in AGENTS.md does not exist`,
          fix: `Update the reference in AGENTS.md or create the missing file.`,
        });
      }
    }
  }

  return violations;
}

const root = join(___linterDir, '..');
const violations = check(root);

if (violations.length > 0) {
  console.error(`\n❌ ${violations.length} stale reference(s) in AGENTS.md:\n`);
  for (const v of violations) {
    console.error(`  Line ${v.line}: ${v.rule}\n    Fix: ${v.fix}\n`);
  }
  process.exit(1);
} else {
  console.log('✅ Doc reference check passed.');
}
