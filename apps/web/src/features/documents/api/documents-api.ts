import { appEnv } from '@/config/env'
import { apiClient } from '@/shared/lib/api-client'
import {
  mockCreateDocument,
  mockGetDocument,
  mockListDocuments,
} from '@/shared/lib/mock-data'
import type {
  CreateDocumentInput,
  DocumentDetail,
  DocumentSummary,
} from '@/shared/types/models'

export async function getDocument(projectSlug: string, docSlug: string) {
  if (appEnv.useMocks) {
    return mockGetDocument(projectSlug, docSlug)
  }

  return apiClient.get<DocumentDetail>(`/projects/${projectSlug}/documents/${docSlug}`)
}

export async function listDocuments(projectSlug: string) {
  if (appEnv.useMocks) {
    return mockListDocuments(projectSlug)
  }

  return apiClient.get<DocumentSummary[]>(`/projects/${projectSlug}/documents`)
}

export async function createDocument(projectSlug: string, input: CreateDocumentInput) {
  if (appEnv.useMocks) {
    return mockCreateDocument(projectSlug, input)
  }

  return apiClient.post<DocumentDetail>(`/projects/${projectSlug}/documents`, input)
}
