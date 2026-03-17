import { fileURLToPath } from 'url';
import { dirname } from 'path';
const ___linterDir = dirname(fileURLToPath(import.meta.url));
/**
 * Structural linter: layer dependency direction.
 * See conventions/architecture.md + conventions/linters.md
 *
 * Layers (top → bottom):
 *   UI → Runtime → Service → Repository → Config → Types
 *
 * Rule: imports must point downward only.
 */
import { readdirSync, readFileSync } from 'fs';
import { join, relative } from 'path';

const LAYERS: Record<string, number> = {
  controller: 5,
  guard: 5,
  filter: 5,
  interceptor: 5,
  pipe: 5,
  module: 5,
  strategy: 4,
  service: 4,
  repository: 3,
  config: 2,
  dto: 1,
  types: 1,
  constants: 1,
  errors: 1,
  mappers: 1,
  decorator: 1,
  utils: 1,
  client: 3,
};

interface Violation {
  file: string;
  importPath: string;
  rule: string;
  fix: string;
}

function getLayer(filename: string): number | null {
  for (const [suffix, level] of Object.entries(LAYERS)) {
    if (filename.includes(`.${suffix}.`)) return level;
  }
  return null;
}

function walk(dir: string): string[] {
  const results: string[] = [];
  try {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.name === 'node_modules' || entry.name === 'dist') continue;
      if (entry.isDirectory()) results.push(...walk(full));
      else if (entry.name.endsWith('.ts') && !entry.name.includes('.spec.')) {
        results.push(full);
      }
    }
  } catch { /* skip unreadable dirs */ }
  return results;
}

function check(apiSrc: string): Violation[] {
  const violations: Violation[] = [];
  const files = walk(apiSrc);

  for (const file of files) {
    const rel = relative(apiSrc, file);
    const fileLayer = getLayer(rel);
    if (fileLayer === null) continue;

    const content = readFileSync(file, 'utf-8');
    const importRegex = /from\s+['"]\.\.?\/(.*?)['"]/g;
    let match: RegExpExecArray | null;

    while ((match = importRegex.exec(content)) !== null) {
      const importedPath = match[1];
      const importLayer = getLayer(importedPath);
      if (importLayer !== null && importLayer > fileLayer) {
        violations.push({
          file: rel,
          importPath: match[0],
          rule: `UPWARD_IMPORT: Layer ${fileLayer} file imports layer ${importLayer}`,
          fix: `Move the dependency to a lower layer or use dependency injection. See conventions/architecture.md`,
        });
      }
    }
  }

  return violations;
}

const apiSrc = join(___linterDir, '..', 'apps', 'api', 'src');
const violations = check(apiSrc);

if (violations.length > 0) {
  console.error(`\n❌ ${violations.length} import violation(s):\n`);
  for (const v of violations) {
    console.error(`  ${v.rule}\n    File: ${v.file}\n    Import: ${v.importPath}\n    Fix: ${v.fix}\n`);
  }
  process.exit(1);
} else {
  console.log('✅ Import direction check passed.');
}
