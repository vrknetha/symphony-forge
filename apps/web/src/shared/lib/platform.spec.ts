import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  mockCreateDocument,
  mockCreateProject,
  mockGetDocument,
  mockGetProject,
  mockListAgentKeys,
  mockListDocuments,
  mockListProjects,
  resetMocks,
} from '@/shared/lib/mock-data'

beforeEach(() => {
  resetMocks()
  vi.clearAllMocks()
  vi.resetModules()
  vi.unstubAllEnvs()
})

describe('platform helpers', () => {
  it('parses env defaults and explicit Azure scopes', async () => {
    let envModule = await import('@/config/env')
    expect(envModule.appEnv.azureScopes).toEqual(['openid', 'profile', 'email'])
    expect(envModule.appEnv.useMocks).toBe(true)

    vi.resetModules()
    vi.stubEnv('VITE_AZURE_SCOPES', 'api://forge/read, profile')
    vi.stubEnv('VITE_USE_MOCKS', 'false')
    envModule = await import('@/config/env')
    expect(envModule.appEnv.azureScopes).toEqual(['api://forge/read', 'profile'])
    expect(envModule.appEnv.useMocks).toBe(false)
  })

  it('manages mock projects, documents, and error cases', () => {
    expect(mockListProjects()).toHaveLength(2)
    const project = mockCreateProject({ description: 'Shared pilot space', name: 'Discovery Hub' })
    expect(project.slug).toBe('discovery-hub')
    expect(mockGetProject(project.slug).members).toHaveLength(1)

    expect(mockListDocuments(project.slug)).toEqual([])
    const document = mockCreateDocument(project.slug, { docType: 'ADR', title: 'Auth decisions' })
    expect(mockGetDocument(project.slug, document.slug).proofDocSlug).toContain(project.slug)
    expect(mockListProjects()[0]?.documentCount).toBe(1)
    expect(mockListAgentKeys()).toHaveLength(2)

    expect(() => mockGetProject('missing-project')).toThrow('Project not found.')
    expect(() => mockGetDocument(project.slug, 'missing-doc')).toThrow('Document not found.')
  })

  it('initializes MSAL, handles redirects, and returns access tokens', async () => {
    const interactionError = class extends Error {}
    const msal = {
      acquireTokenSilent: vi.fn<() => Promise<{ accessToken: string }>>(() => Promise.resolve({ accessToken: 'token-123' })),
      getActiveAccount: vi.fn<() => { id: string } | null>(() => ({ id: 'active' })),
      getAllAccounts: vi.fn<() => Array<{ id: string }>>(() => [{ id: 'fallback' }]),
      handleRedirectPromise: vi.fn<() => Promise<{ account: { id: string } }>>(
        () => Promise.resolve({ account: { id: 'redirect' } }),
      ),
      initialize: vi.fn<() => Promise<void>>(() => Promise.resolve()),
      setActiveAccount: vi.fn<(account: { id: string }) => void>(),
    }

    vi.doMock('@azure/msal-browser', () => ({
      InteractionRequiredAuthError: interactionError,
      PublicClientApplication: vi.fn(() => msal),
    }))
    vi.doMock('@/config/env', () => ({
      appEnv: {
        azureAuthority: 'https://login.microsoftonline.com/common',
        azureClientId: 'client-id',
        azureRedirectUri: 'http://localhost:5173',
        azureScopes: ['openid'],
        useMocks: false,
      },
    }))

    const client = await import('@/features/auth/msal/client')
    await client.initializeMsal()
    expect(msal.initialize).toHaveBeenCalledOnce()
    expect(msal.handleRedirectPromise).toHaveBeenCalledOnce()
    expect(msal.setActiveAccount).toHaveBeenCalledWith({ id: 'redirect' })
    expect(await client.acquireAccessToken()).toBe('token-123')

    msal.getActiveAccount.mockReturnValueOnce(null)
    msal.getAllAccounts.mockReturnValueOnce([])
    await expect(client.acquireAccessToken()).rejects.toThrow('No authenticated account is available.')

    msal.getActiveAccount.mockReturnValueOnce({ id: 'active' })
    msal.acquireTokenSilent.mockRejectedValueOnce(new interactionError('auth'))
    await expect(client.acquireAccessToken()).rejects.toThrow(
      'Authentication is required before calling the API.',
    )

    const genericError = new Error('boom')
    msal.acquireTokenSilent.mockRejectedValueOnce(genericError)
    await expect(client.acquireAccessToken()).rejects.toBe(genericError)
  })

  it('sends authenticated API requests and handles failures', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    vi.doMock('@/config/env', () => ({ appEnv: { apiBaseUrl: 'http://localhost:3000/api/v1' } }))
    vi.doMock('@/features/auth/msal/client', () => ({
      acquireAccessToken: vi.fn(() => Promise.resolve('jwt-token')),
    }))

    fetchMock.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ data: { name: 'Forge' } }), status: 200 })
    fetchMock.mockResolvedValueOnce({ ok: true, status: 204 })
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500 })

    const { apiClient } = await import('@/shared/lib/api-client')
    expect(await apiClient.get<{ name: string }>('/projects')).toEqual({ name: 'Forge' })
    await expect(apiClient.delete('/projects/forge')).resolves.toBeUndefined()
    await expect(apiClient.post('/projects', { name: 'Forge' })).rejects.toThrow(
      'Request failed with status 500',
    )
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ credentials: 'include' })
  })

  it('uses real API client branches when mock mode is disabled', async () => {
    const apiClient = {
      get: vi.fn(() => Promise.resolve(['ok'])),
      post: vi.fn(() => Promise.resolve({ slug: 'created' })),
    }

    vi.doMock('@/config/env', () => ({ appEnv: { useMocks: false } }))
    vi.doMock('@/shared/lib/api-client', () => ({ apiClient }))
    vi.doMock('@/shared/lib/mock-data', () => ({
      mockCreateDocument: vi.fn(),
      mockCreateProject: vi.fn(),
      mockGetDocument: vi.fn(),
      mockGetProject: vi.fn(),
      mockListAgentKeys: vi.fn(),
      mockListDocuments: vi.fn(),
      mockListProjects: vi.fn(),
    }))

    const projectsApi = await import('@/features/projects/api/projects-api')
    const documentsApi = await import('@/features/documents/api/documents-api')
    const settingsApi = await import('@/features/settings/api/settings-api')

    await projectsApi.listProjects()
    await projectsApi.getProject('forge')
    await projectsApi.createProject({ description: 'desc', name: 'Forge' })
    await documentsApi.listDocuments('forge')
    await documentsApi.getDocument('forge', 'plan')
    await documentsApi.createDocument('forge', { docType: 'PLAN', title: 'Plan' })
    await settingsApi.listAgentKeys()

    expect(apiClient.get).toHaveBeenCalledWith('/projects')
    expect(apiClient.get).toHaveBeenCalledWith('/projects/forge')
    expect(apiClient.post).toHaveBeenCalledWith('/projects', { description: 'desc', name: 'Forge' })
    expect(apiClient.get).toHaveBeenCalledWith('/projects/forge/documents')
    expect(apiClient.get).toHaveBeenCalledWith('/projects/forge/documents/plan')
    expect(apiClient.post).toHaveBeenCalledWith('/projects/forge/documents', {
      docType: 'PLAN',
      title: 'Plan',
    })
    expect(apiClient.get).toHaveBeenCalledWith('/agent-keys')
  })
})
