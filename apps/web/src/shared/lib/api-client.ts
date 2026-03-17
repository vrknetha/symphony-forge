import { appEnv } from '@/config/env'
import { acquireAccessToken } from '@/features/auth/msal/client'
import type { ApiEnvelope } from '@/shared/types/models'

// CONVENTION_CONFLICT: `frontend-patterns.md` prefers an orval-generated client,
// but this task explicitly asks for a hand-built MSAL-backed API client and no
// OpenAPI spec is available in the repository yet.
async function request<T>(path: string, init: RequestInit = {}) {
  const token = await acquireAccessToken()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')

  if (!(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${appEnv.apiBaseUrl}${path}`, {
    credentials: 'include',
    ...init,
    headers,
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const json = (await response.json()) as ApiEnvelope<T>
  return json.data
}

export const apiClient = {
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { body: JSON.stringify(body), method: 'POST' }),
}
