export const USER_ROLES = ['ADMIN', 'MEMBER'] as const;
export const PROJECT_STATUSES = ['ACTIVE', 'ARCHIVED'] as const;
export const MEMBER_ROLES = ['OWNER', 'EDITOR', 'VIEWER'] as const;
export const DOC_TYPES = [
  'PLAN',
  'SPEC',
  'ADR',
  'NOTES',
  'RETROSPECTIVE',
] as const;
export const AGENT_KEY_CAPABILITIES = ['read', 'comment', 'edit'] as const;

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;
export const PROJECT_SEARCH_LIMIT = 10;
export const PROOF_PROXY_TIMEOUT_MS = 10_000;

export const DOCUMENT_TEMPLATES: Record<(typeof DOC_TYPES)[number], string> = {
  ADR: '# ADR: [Title]\n\n## Status\nProposed\n\n## Context\n\n\n## Decision\n\n\n## Consequences\n',
  NOTES: '# [Title]\n\n## Notes\n\n',
  PLAN: '# [Title]\n\n## What Are We Building?\n\n\n## Who Is It For?\n\n\n## Success Looks Like\n\n\n## Key Flows\n\n\n## Data Model (Sketch)\n\n\n## Open Questions\n',
  RETROSPECTIVE:
    '# Retro: [Title]\n\n## What Went Well\n\n\n## What Didn\'t\n\n\n## Action Items\n',
  SPEC: '# [Title]\n\n## Overview\n\n\n## Requirements\n\n### Functional\n\n\n### Non-Functional\n\n\n## API Contract\n\n\n## Data Model\n\n\n## Dependencies\n',
};
