import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '@/features/auth/hooks/use-auth'
import { RouteErrorPage } from '@/shared/components/RouteErrorPage'
import { AppShell } from '@/shared/layout/AppShell'

vi.mock('@/features/auth/hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    isRouteErrorResponse: vi.fn(),
    useRouteError: vi.fn(),
  }
})

const mockedUseAuth = vi.mocked(useAuth)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('shared layout', () => {
  it('shows the admin navigation and settings label', () => {
    const logout = vi.fn(() => Promise.resolve())
    mockedUseAuth.mockReturnValue({
      isAdmin: true,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(() => Promise.resolve()),
      logout,
      user: {
        email: 'ravi@knacklabs.ai',
        id: 'user-ravi',
        name: 'Ravi Kiran',
        role: 'ADMIN',
      },
    })

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route element={<div>Settings content</div>} path="/settings" />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Projects' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()
    expect(screen.getAllByText('Settings')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(logout).toHaveBeenCalledOnce()
  })

  it('hides admin links for members and labels project routes correctly', () => {
    mockedUseAuth.mockReturnValue({
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
      <MemoryRouter initialEntries={['/projects/knack-forge']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route element={<div>Project content</div>} path="/projects/:slug" />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument()
    expect(screen.getByText('Project workspace')).toBeInTheDocument()
  })

  it('renders route errors and goes back on click', async () => {
    const routerDom = await import('react-router-dom')
    const back = vi.spyOn(window.history, 'back').mockImplementation(() => undefined)
    vi.mocked(routerDom.isRouteErrorResponse).mockReturnValue(true)
    vi.mocked(routerDom.useRouteError).mockReturnValue({ statusText: 'Missing route' } as never)

    render(<RouteErrorPage />)

    expect(screen.getByText('Missing route')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /go back/i }))
    expect(back).toHaveBeenCalledOnce()
  })

  it('falls back to the generic route error message', async () => {
    const routerDom = await import('react-router-dom')
    vi.mocked(routerDom.isRouteErrorResponse).mockReturnValue(false)
    vi.mocked(routerDom.useRouteError).mockReturnValue(new Error('boom') as never)

    render(<RouteErrorPage />)

    expect(screen.getByText(/something unexpected happened/i)).toBeInTheDocument()
  })
})
