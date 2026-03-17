import type {
  CreateDocumentInput,
  CreateProjectInput,
  ProjectDetail,
  ProjectSummary,
} from '@/shared/types/models'
import {
  initialAgentKeys,
  initialDocuments,
  initialMembers,
  initialProjects,
  raviUser,
} from './mock-seed'
import { slugify } from './slug'

let projects = [...initialProjects]
let projectDocuments = structuredClone(initialDocuments)
let projectMembers = structuredClone(initialMembers)
let agentKeys = [...initialAgentKeys]

function updateProjectSummary(projectSlug: string) {
  const documents = projectDocuments[projectSlug] ?? []

  projects = projects.map((project) =>
    project.slug === projectSlug
      ? {
          ...project,
          documentCount: documents.length,
          lastActive: documents[0]?.lastUpdated ?? project.lastActive,
        }
      : project,
  )
}

export const mockSessionUser = raviUser

export function resetMocks() {
  agentKeys = [...initialAgentKeys]
  projectDocuments = structuredClone(initialDocuments)
  projectMembers = structuredClone(initialMembers)
  projects = [...initialProjects]
}

export function mockListProjects() {
  return [...projects]
}

export function mockGetProject(projectSlug: string) {
  const project = projects.find((item) => item.slug === projectSlug)

  if (!project) {
    throw new Error('Project not found.')
  }

  return {
    ...project,
    members: [...(projectMembers[projectSlug] ?? [])],
  } satisfies ProjectDetail
}

export function mockCreateProject(input: CreateProjectInput) {
  const slug = slugify(input.name)
  const project = {
    description: input.description,
    documentCount: 0,
    id: `project-${slug}`,
    lastActive: new Date().toISOString(),
    name: input.name,
    slug,
    status: 'ACTIVE',
  } satisfies ProjectSummary

  projects = [project, ...projects]
  projectDocuments[slug] = []
  projectMembers[slug] = [raviUser]
  return project
}

export function mockListDocuments(projectSlug: string) {
  return [...(projectDocuments[projectSlug] ?? [])]
}

export function mockGetDocument(projectSlug: string, docSlug: string) {
  const document = projectDocuments[projectSlug]?.find((item) => item.slug === docSlug)

  if (!document) {
    throw new Error('Document not found.')
  }

  return document
}

export function mockCreateDocument(projectSlug: string, input: CreateDocumentInput) {
  const slug = slugify(input.title)
  const document = {
    authorName: raviUser.name,
    docType: input.docType,
    id: `doc-${projectSlug}-${slug}`,
    lastUpdated: new Date().toISOString(),
    proofDocSlug: `${projectSlug}-${slug}`,
    proofUrl: `/documents/${projectSlug}-${slug}`,
    slug,
    title: input.title,
    versionLabel: 'Just created',
  }

  projectDocuments[projectSlug] = [document, ...(projectDocuments[projectSlug] ?? [])]
  updateProjectSummary(projectSlug)
  return document
}

export function mockListAgentKeys() {
  return [...agentKeys]
}
