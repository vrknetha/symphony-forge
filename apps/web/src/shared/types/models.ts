export const docTypes = ['PLAN', 'SPEC', 'ADR', 'NOTES', 'RETROSPECTIVE'] as const
export const projectStatuses = ['ACTIVE', 'ARCHIVED'] as const
export const appRoles = ['ADMIN', 'MEMBER'] as const

export type AppRole = (typeof appRoles)[number]
export type DocType = (typeof docTypes)[number]
export type ProjectStatus = (typeof projectStatuses)[number]

export interface AuthUser {
  email: string
  id: string
  name: string
  role: AppRole
}

export interface DocumentSummary {
  authorName: string
  docType: DocType
  id: string
  lastUpdated: string
  proofDocSlug: string
  slug: string
  title: string
}

export interface DocumentDetail extends DocumentSummary {
  proofUrl: string
  versionLabel: string
}

export interface ProjectSummary {
  description: string
  documentCount: number
  id: string
  lastActive: string
  name: string
  slug: string
  status: ProjectStatus
}

export interface ProjectDetail extends ProjectSummary {
  members: AuthUser[]
}

export interface AgentKeySummary {
  active: boolean
  capabilities: string[]
  id: string
  keyPrefix: string
  lastUsedAt: string | null
  name: string
}

export interface CreateProjectInput {
  description: string
  name: string
}

export interface CreateDocumentInput {
  docType: DocType
  title: string
}

export interface ApiEnvelope<T> {
  data: T
}
