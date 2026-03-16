import { DocType } from '@prisma/client';

export const DOCUMENT_TEMPLATES: Record<DocType, string> = {
  ADR: '# ADR: [Title]\n\n## Status\nProposed\n\n## Context\n\n\n## Decision\n\n\n## Consequences\n',
  NOTES: '# [Title]\n\n## Notes\n\n',
  PLAN: '# [Title]\n\n## What Are We Building?\n\n\n## Who Is It For?\n\n\n## Success Looks Like\n',
  RETROSPECTIVE:
    "# Retro: [Title]\n\n## What Went Well\n\n\n## What Didn't\n\n\n## Action Items\n",
  SPEC: '# [Title]\n\n## Overview\n\n\n## Requirements\n\n### Functional\n\n\n### Non-Functional\n',
};
