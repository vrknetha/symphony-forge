import type {
  AgentKeySummary,
  AuthUser,
  DocumentDetail,
  ProjectSummary,
} from '@/shared/types/models'

export const raviUser: AuthUser = {
  email: 'ravi@knacklabs.ai',
  id: 'user-ravi',
  name: 'Ravi Kiran',
  role: 'ADMIN',
}

export const mayaUser: AuthUser = {
  email: 'maya@knacklabs.ai',
  id: 'user-maya',
  name: 'Maya Chen',
  role: 'MEMBER',
}

export const initialProjects: ProjectSummary[] = [
  {
    description: 'Projects + Documents foundation for KnackLabs engineering work.',
    documentCount: 2,
    id: 'project-forge',
    lastActive: '2026-03-16T16:00:00.000Z',
    name: 'Knack Forge',
    slug: 'knack-forge',
    status: 'ACTIVE',
  },
  {
    description: 'Internal operating model, onboarding notes, and experiment templates.',
    documentCount: 1,
    id: 'project-ops',
    lastActive: '2026-03-14T12:30:00.000Z',
    name: 'Platform Operations',
    slug: 'platform-operations',
    status: 'ACTIVE',
  },
]

export const initialDocuments: Record<string, DocumentDetail[]> = {
  'knack-forge': [
    {
      authorName: raviUser.name,
      docType: 'PLAN',
      id: 'doc-plan',
      lastUpdated: '2026-03-16T16:00:00.000Z',
      proofDocSlug: 'knack-forge-plan',
      proofUrl: '/documents/knack-forge-plan',
      slug: 'v1-platform-plan',
      title: 'V1 Platform Plan',
      versionLabel: 'Live collaborative draft',
    },
    {
      authorName: mayaUser.name,
      docType: 'SPEC',
      id: 'doc-spec',
      lastUpdated: '2026-03-15T11:30:00.000Z',
      proofDocSlug: 'proof-spec-shell',
      proofUrl: '/documents/proof-spec-shell',
      slug: 'editor-embed-spec',
      title: 'Editor Embed Spec',
      versionLabel: 'Updated 3 hours ago',
    },
  ],
  'platform-operations': [
    {
      authorName: mayaUser.name,
      docType: 'NOTES',
      id: 'doc-ops',
      lastUpdated: '2026-03-14T12:30:00.000Z',
      proofDocSlug: 'platform-ops-weekly',
      proofUrl: '/documents/platform-ops-weekly',
      slug: 'weekly-sync',
      title: 'Weekly Sync Notes',
      versionLabel: 'Updated yesterday',
    },
  ],
}

export const initialMembers: Record<string, AuthUser[]> = {
  'knack-forge': [raviUser, mayaUser],
  'platform-operations': [raviUser, mayaUser],
}

export const initialAgentKeys: AgentKeySummary[] = [
  {
    active: true,
    capabilities: ['read', 'comment'],
    id: 'agent-codex',
    keyPrefix: 'codex-1a2b',
    lastUsedAt: '2026-03-16T09:15:00.000Z',
    name: 'codex-worker',
  },
  {
    active: true,
    capabilities: ['read', 'edit'],
    id: 'agent-proof',
    keyPrefix: 'proof-9f8e',
    lastUsedAt: '2026-03-15T18:45:00.000Z',
    name: 'proof-sync',
  },
]
