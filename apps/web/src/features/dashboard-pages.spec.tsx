import type { ReactElement } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '@/features/auth/hooks/use-auth'
import { AuthGuard } from '@/features/auth/components/AuthGuard'
import { AdminGuard } from '@/features/auth/components/AdminGuard'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { useDocument } from '@/features/documents/hooks/use-document'
import { useDocuments } from '@/features/documents/hooks/use-documents'
import { DocumentEditorPage } from '@/features/documents/pages/DocumentEditorPage'
import { useProject } from '@/features/projects/hooks/use-project'
import { useProjects } from '@/features/projects/hooks/use-projects'
import { ProjectDetailPage } from '@/features/projects/pages/ProjectDetailPage'
import { ProjectsPage } from '@/features/projects/pages/ProjectsPage'
import { useAgentKeys } from '@/features/settings/hooks/use-agent-keys'
import { SettingsPage } from '@/features/settings/pages/SettingsPage'
import { initialAgentKeys, initialDocuments, initialProjects } from '@/shared/lib/mock-seed'
import { createQueryClient } from '@/shared/lib/query-client'

vi.mock('@/features/auth/hooks/use-auth', () => ({ useAuth: vi.fn() }))
vi.mock('@/features/projects/hooks/use-projects', () => ({ useProjects: vi.fn() }))
vi.mock('@/features/projects/hooks/use-project', () => ({ useProject: vi.fn() }))
vi.mock('@/features/documents/hooks/use-documents', () => ({ useDocuments: vi.fn() }))
vi.mock('@/features/documents/hooks/use-document', () => ({ useDocument: vi.fn() }))
vi.mock('@/features/settings/hooks/use-agent-keys', () => ({ useAgentKeys: vi.fn() }))

const mockedUseAuth = vi.mocked(useAuth)
const mockedUseProjects = vi.mocked(useProjects)
const mockedUseProject = vi.mocked(useProject)
const mockedUseDocuments = vi.mocked(useDocuments)
const mockedUseDocument = vi.mocked(useDocument)
const mockedUseAgentKeys = vi.mocked(useAgentKeys)


function renderWithQuery(ui: ReactElement) {
  return render(<QueryClientProvider client={createQueryClient()}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  mockedUseAuth.mockReturnValue({
    isAdmin: true,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(() => Promise.resolve()),
    logout: vi.fn(() => Promise.resolve()),
    user: {
      email: 'ravi@knacklabs.ai',
      id: 'user-ravi',
      name: 'Ravi Kiran',
      role: 'ADMIN',
    },
  })
})

describe('dashboard page states', () => {
  it('shows the auth guard loading state and redirects unauthenticated users', () => {
    mockedUseAuth.mockReturnValueOnce({
      isAdmin: false,
      isAuthenticated: false,
      isLoading: true,
      login: vi.fn(() => Promise.resolve()),
      logout: vi.fn(() => Promise.resolve()),
      user: null,
    })

    renderWithQuery(
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route element={<AuthGuard />}>
            <Route element={<div>Protected</div>} path="/projects" />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText(/preparing your workspace/i)).toBeInTheDocument()

    mockedUseAuth.mockReturnValueOnce({
      isAdmin: false,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(() => Promise.resolve()),
      logout: vi.fn(() => Promise.resolve()),
      user: null,
    })

    render(
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route element={<AuthGuard />}>
            <Route element={<div>Protected</div>} path="/projects" />
          </Route>
          <Route element={<div>Login</div>} path="/login" />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Login')).toBeInTheDocument()
  })

  it('allows admins, redirects the login page, and blocks settings for members', () => {
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route element={<AdminGuard />}>
            <Route element={<div>Settings</div>} path="/settings" />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Settings')).toBeInTheDocument()

    mockedUseAuth.mockReturnValueOnce({
      isAdmin: false,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(() => Promise.resolve()),
      logout: vi.fn(() => Promise.resolve()),
      user: {
        email: 'maya@knacklabs.ai',
        id: 'user-maya',
        name: 'Maya Chen',
        role: 'MEMBER',
      },
    })

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route element={<AdminGuard />}>
            <Route element={<div>Settings</div>} path="/settings" />
          </Route>
          <Route element={<div>Projects</div>} path="/projects" />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Projects')).toBeInTheDocument()

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route element={<LoginPage />} path="/login" />
          <Route element={<div>Projects</div>} path="/projects" />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Projects')[0]).toBeInTheDocument()
  })

  it('renders projects loading, error, and empty search states', () => {
    mockedUseProjects.mockReturnValue({ data: undefined, error: null, isLoading: true } as never)
    const loadingView = renderWithQuery(
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route element={<ProjectsPage />} path="/projects" />
        </Routes>
      </MemoryRouter>,
    )
    expect(document.querySelectorAll('.animate-pulse')).toHaveLength(2)

    loadingView.unmount()
    mockedUseProjects.mockReturnValue({ data: undefined, error: new Error('boom'), isLoading: false } as never)
    const errorView = renderWithQuery(
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route element={<ProjectsPage />} path="/projects" />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText(/failed to load projects/i)).toBeInTheDocument()

    errorView.unmount()
    mockedUseProjects.mockReturnValue({ data: initialProjects, error: null, isLoading: false } as never)
    render(
      <MemoryRouter initialEntries={['/projects']}>
        <Routes>
          <Route element={<ProjectsPage />} path="/projects" />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByPlaceholderText('Search projects'), { target: { value: 'zzz' } })
    expect(screen.getByText(/no projects match the current filter/i)).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('Search projects'), { target: { value: '' } })
    expect(screen.getByText('Knack Forge')).toBeInTheDocument()
  })

  it('renders project detail loading, error, and filtered empty states', () => {
    mockedUseProject.mockReturnValue({ data: undefined, error: null, isLoading: true } as never)
    mockedUseDocuments.mockReturnValue({ data: undefined, error: null, isLoading: false } as never)
    const loadingView = renderWithQuery(
      <MemoryRouter initialEntries={['/projects/knack-forge']}>
        <Routes>
          <Route element={<ProjectDetailPage />} path="/projects/:slug" />
        </Routes>
      </MemoryRouter>,
    )
    expect(document.querySelectorAll('.animate-pulse')).toHaveLength(2)

    loadingView.unmount()
    mockedUseProject.mockReturnValue({ data: undefined, error: new Error('boom'), isLoading: false } as never)
    mockedUseDocuments.mockReturnValue({ data: undefined, error: null, isLoading: false } as never)
    const errorView = renderWithQuery(
      <MemoryRouter initialEntries={['/projects/knack-forge']}>
        <Routes>
          <Route element={<ProjectDetailPage />} path="/projects/:slug" />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText(/failed to load this project/i)).toBeInTheDocument()

    errorView.unmount()
    mockedUseProject.mockReturnValue({ data: { ...initialProjects[0], members: [] }, error: null, isLoading: false } as never)
    mockedUseDocuments.mockReturnValue({ data: initialDocuments['knack-forge'], error: null, isLoading: false } as never)
    renderWithQuery(
      <MemoryRouter initialEntries={['/projects/knack-forge']}>
        <Routes>
          <Route element={<ProjectDetailPage />} path="/projects/:slug" />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByPlaceholderText('Search documents'), { target: { value: 'zzz' } })
    expect(screen.getByText(/no documents match the current filters/i)).toBeInTheDocument()
    fireEvent.change(screen.getByDisplayValue('ALL'), { target: { value: 'PLAN' } })
    fireEvent.change(screen.getByPlaceholderText('Search documents'), { target: { value: '' } })
    expect(screen.getByText('V1 Platform Plan')).toBeInTheDocument()
  })

  it('renders the document editor loading and error states', () => {
    mockedUseProject.mockReturnValueOnce({ data: undefined, error: null, isLoading: true } as never)
    mockedUseDocument.mockReturnValueOnce({ data: undefined, error: null, isLoading: false } as never)
    const loadingView = render(
      <MemoryRouter initialEntries={['/projects/knack-forge/docs/v1-platform-plan']}>
        <Routes>
          <Route element={<DocumentEditorPage />} path="/projects/:slug/docs/:docSlug" />
        </Routes>
      </MemoryRouter>,
    )
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()

    loadingView.unmount()
    mockedUseProject.mockReturnValue({ data: undefined, error: new Error('boom'), isLoading: false } as never)
    mockedUseDocument.mockReturnValue({ data: undefined, error: null, isLoading: false } as never)
    render(
      <MemoryRouter initialEntries={['/projects/knack-forge/docs/v1-platform-plan']}>
        <Routes>
          <Route element={<DocumentEditorPage />} path="/projects/:slug/docs/:docSlug" />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText(/failed to load this document/i)).toBeInTheDocument()
  })

  it('renders settings loading, error, empty, and revoked key states', () => {
    mockedUseAgentKeys.mockReturnValueOnce({ data: undefined, error: null, isLoading: true } as never)
    const { rerender } = render(<SettingsPage />)
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()

    mockedUseAgentKeys.mockReturnValueOnce({ data: undefined, error: new Error('boom'), isLoading: false } as never)
    rerender(<SettingsPage />)
    expect(screen.getByText(/failed to load agent keys/i)).toBeInTheDocument()

    mockedUseAgentKeys.mockReturnValueOnce({ data: [], error: null, isLoading: false } as never)
    rerender(<SettingsPage />)
    expect(screen.getByText(/no agent keys are configured yet/i)).toBeInTheDocument()

    mockedUseAgentKeys.mockReturnValue({
      data: [{ ...initialAgentKeys[0], active: false, lastUsedAt: null }],
      error: null,
      isLoading: false,
    } as never)
    rerender(<SettingsPage />)
    expect(screen.getByText(/revoked · never used/i)).toBeInTheDocument()
  })
})
