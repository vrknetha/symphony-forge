import { fileURLToPath } from 'url';
import { dirname } from 'path';
const ___linterDir = dirname(fileURLToPath(import.meta.url));
/**
 * Structural linter: module boundary enforcement.
 * See conventions/design-patterns.md + conventions/linters.md
 *
 * Rule: No cross-domain imports except through shared interfaces.
 * Auth guards are the only cross-domain exception.
 */
import { readdirSync, readFileSync, existsSync } from 'fs';
import { join, relative, dirname, basename } from 'path';

interface Violation {
  file: string;
  importedModule: string;
  sourceModule: string;
  rule: string;
  fix: string;
}

function getModuleDirs(apiSrc: string): string[] {
  if (!existsSync(apiSrc)) return [];
  return readdirSync(apiSrc, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .filter((d) => !['common', 'config', 'prisma', 'health'].includes(d.name))
    .map((d) => d.name);
}

function getDomain(filePath: string): string | null {
  const parts = filePath.split('/');
  return parts[0] || null;
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
  } catch { /* skip */ }
  return results;
}

function check(apiSrc: string): Violation[] {
  const violations: Violation[] = [];
  const modules = new Set(getModuleDirs(apiSrc));
  const files = walk(apiSrc);

  for (const file of files) {
    const rel = relative(apiSrc, file);
    const sourceDomain = getDomain(rel);
    if (!sourceDomain || !modules.has(sourceDomain)) continue;

    const content = readFileSync(file, 'utf-8');
    const importRegex = /from\s+['"]\.\.\/([^/'"]+)\//g;
    let match: RegExpExecArray | null;

    while ((match = importRegex.exec(content)) !== null) {
      const importedModule = match[1];

      // Skip allowed cross-domain imports
      if (importedModule === 'common') continue;
      if (importedModule === 'config') continue;
      if (importedModule === 'prisma') continue;
      if (importedModule === 'health') continue;

      // Auth guards are the only exception
      if (importedModule === 'auth' && file.includes('.guard.')) continue;
      if (importedModule === 'auth' && file.includes('.module.')) continue;

      if (modules.has(importedModule) && importedModule !== sourceDomain) {
        violations.push({
          file: rel,
          importedModule,
          sourceModule: sourceDomain,
          rule: `CROSS_DOMAIN_IMPORT: ${sourceDomain} imports ${importedModule} internals`,
          fix: `Use events or shared interfaces. Modules must not import each other's services/repositories. See conventions/design-patterns.md`,
        });
      }
    }
  }

  return violations;
}

const apiSrc = join(___linterDir, '..', 'apps', 'api', 'src');
const violations = check(apiSrc);

if (violations.length > 0) {
  console.error(`\n❌ ${violations.length} boundary violation(s):\n`);
  for (const v of violations) {
    console.error(
      `  ${v.rule}\n    File: ${v.file}\n    Fix: ${v.fix}\n`,
    );
  }
  process.exit(1);
} else {
  console.log('✅ Module boundary check passed.');
}
