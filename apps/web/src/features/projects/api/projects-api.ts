import { appEnv } from '@/config/env'
import { apiClient } from '@/shared/lib/api-client'
import {
  mockCreateProject,
  mockGetProject,
  mockListProjects,
} from '@/shared/lib/mock-data'
import type {
  CreateProjectInput,
  ProjectDetail,
  ProjectSummary,
} from '@/shared/types/models'

export async function getProject(slug: string) {
  if (appEnv.useMocks) {
    return mockGetProject(slug)
  }

  return apiClient.get<ProjectDetail>(`/projects/${slug}`)
}

export async function listProjects() {
  if (appEnv.useMocks) {
    return mockListProjects()
  }

  return apiClient.get<ProjectSummary[]>('/projects')
}

export async function createProject(input: CreateProjectInput) {
  if (appEnv.useMocks) {
    return mockCreateProject(input)
  }

  return apiClient.post<ProjectSummary>('/projects', input)
}
