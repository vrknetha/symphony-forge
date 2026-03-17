import type { ReactElement } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminGuard } from '@/features/auth/components/AdminGuard'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { useAuth } from '@/features/auth/hooks/use-auth'
import { DocumentEditorPage } from '@/features/documents/pages/DocumentEditorPage'
import { ProjectDetailPage } from '@/features/projects/pages/ProjectDetailPage'
import { ProjectsPage } from '@/features/projects/pages/ProjectsPage'
import { SettingsPage } from '@/features/settings/pages/SettingsPage'
import { createQueryClient } from '@/shared/lib/query-client'

vi.mock('@/features/auth/hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

const mockedUseAuth = vi.mocked(useAuth)

function renderWithRouter(
  initialEntry: string,
  routes: ReactElement,
  authOverride: Partial<ReturnType<typeof useAuth>> = {},
) {
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
    ...authOverride,
  })

  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>{routes}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('web dashboard pages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the login page for unauthenticated users', async () => {
    renderWithRouter(
      '/login',
      <Routes>
        <Route element={<LoginPage />} path="/login" />
      </Routes>,
      {
        isAdmin: false,
        isAuthenticated: false,
        user: null,
      },
    )

    expect(
      await screen.findByRole('heading', { name: /collaborative project memory/i }),
    ).toBeInTheDocument()
  })

  it('creates a project from the projects page', async () => {
    renderWithRouter(
      '/projects',
      <Routes>
        <Route element={<ProjectsPage />} path="/projects" />
        <Route element={<ProjectDetailPage />} path="/projects/:slug" />
      </Routes>,
    )

    expect(await screen.findByText('Knack Forge')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /new project/i }))
    fireEvent.change(screen.getByLabelText('Name'), {
      target: { value: 'Discovery Hub' },
    })
    fireEvent.change(screen.getByLabelText('Description'), {
      target: { value: 'Shared discovery work for pilots.' },
    })
    fireEvent.submit(screen.getByRole('button', { name: /create project/i }).closest('form')!)

    await waitFor(() => {
      expect(screen.getByText('Discovery Hub')).toBeInTheDocument()
    })
  })

  it('creates a document from project detail', async () => {
    renderWithRouter(
      '/projects/knack-forge',
      <Routes>
        <Route element={<ProjectDetailPage />} path="/projects/:slug" />
        <Route element={<DocumentEditorPage />} path="/projects/:slug/docs/:docSlug" />
      </Routes>,
    )

    expect(await screen.findByText('V1 Platform Plan')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /new document/i }))
    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'Launch Retro' },
    })
    fireEvent.change(screen.getByDisplayValue('PLAN'), {
      target: { value: 'RETROSPECTIVE' },
    })
    fireEvent.submit(screen.getByRole('button', { name: /create document/i }).closest('form')!)

    expect(await screen.findByText(/proof document slug/i)).toBeInTheDocument()
    expect(screen.getByText('RETROSPECTIVE')).toBeInTheDocument()
  })

  it('toggles the document sidebar', async () => {
    renderWithRouter(
      '/projects/knack-forge/docs/v1-platform-plan',
      <Routes>
        <Route element={<DocumentEditorPage />} path="/projects/:slug/docs/:docSlug" />
      </Routes>,
    )

    expect(await screen.findByText('Live collaborative draft')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /collapse/i }))

    await waitFor(() => {
      expect(screen.queryByText('Live collaborative draft')).not.toBeInTheDocument()
    })
  })

  it('redirects non-admin users away from settings', async () => {
    renderWithRouter(
      '/settings',
      <Routes>
        <Route element={<AdminGuard />} path="/settings">
          <Route element={<div>Settings</div>} index />
        </Route>
        <Route element={<h1>Projects redirect</h1>} path="/projects" />
      </Routes>,
      {
        isAdmin: false,
        user: {
          email: 'maya@knacklabs.ai',
          id: 'user-maya',
          name: 'Maya Chen',
          role: 'MEMBER',
        },
      },
    )

    expect(await screen.findByRole('heading', { name: 'Projects redirect' })).toBeInTheDocument()
  })

  it('shows agent keys for admins', async () => {
    renderWithRouter(
      '/settings',
      <Routes>
        <Route element={<SettingsPage />} path="/settings" />
      </Routes>,
    )

    expect(await screen.findByText('codex-worker')).toBeInTheDocument()
    expect(screen.getByText('proof-sync')).toBeInTheDocument()
  })
})
