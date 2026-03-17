import type { ReactNode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

beforeEach(() => {
  document.body.innerHTML = '<div id="root"></div>'
  vi.clearAllMocks()
  vi.resetModules()
  vi.unmock('@/app/router')
  vi.unmock('react-router-dom')
})

describe('app bootstrap modules', () => {
  it('declares the required public and protected routes', async () => {
    const { appRoutes } = await import('@/app/route-config')

    expect(appRoutes[0]?.path).toBe('/login')
    expect(appRoutes[1]?.children?.[0]?.children?.map((route) => route.path ?? 'index')).toEqual([
      'index',
      '/projects',
      '/projects/:slug',
      '/projects/:slug/docs/:docSlug',
      'index',
    ])
  })

  it('renders the router from App', async () => {
    vi.doMock('@/app/router', () => ({ AppRouter: () => <div>router-view</div> }))

    const { App } = await import('@/app/App')
    render(<App />)
    expect(screen.getByText('router-view')).toBeInTheDocument()
  })

  it('creates a browser router and hands it to RouterProvider', async () => {
    vi.doMock('react-router-dom', async () => {
      const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
      return {
        ...actual,
        RouterProvider: ({ router }: { router: { id: string } }) => <div>{router.id}</div>,
        createBrowserRouter: vi.fn(() => ({ id: 'router' })),
      }
    })

    const { AppRouter } = await import('@/app/router')
    render(<AppRouter />)
    expect(screen.getByText('router')).toBeInTheDocument()
  })

  it('wraps children with the MSAL, auth, and query providers', async () => {
    vi.doMock('@azure/msal-react', () => ({
      MsalProvider: ({ children }: { children: ReactNode }) => <div data-testid="msal">{children}</div>,
    }))
    vi.doMock('@tanstack/react-query', () => ({
      QueryClientProvider: ({ children }: { children: ReactNode }) => <div data-testid="query">{children}</div>,
    }))
    vi.doMock('@/features/auth/providers/AuthProvider', () => ({
      AuthProvider: ({ children }: { children: ReactNode }) => <div data-testid="auth">{children}</div>,
    }))
    vi.doMock('@/features/auth/msal/client', () => ({ msalInstance: { id: 'msal-instance' } }))
    vi.doMock('@/shared/lib/query-client', () => ({ createQueryClient: () => ({ id: 'query-client' }) }))

    const { AppProviders } = await import('@/app/providers')
    render(
      <AppProviders>
        <span>child</span>
      </AppProviders>,
    )

    expect(screen.getByTestId('msal')).toBeInTheDocument()
    expect(screen.getByTestId('auth')).toBeInTheDocument()
    expect(screen.getByTestId('query')).toBeInTheDocument()
    expect(screen.getByText('child')).toBeInTheDocument()
  })

  it('bootstraps MSAL before rendering the app root', async () => {
    const appRender = vi.fn()
    const createRoot = vi.fn(() => ({ render: appRender }))
    const initializeMsal = vi.fn(() => Promise.resolve())

    vi.doMock('react-dom/client', () => ({ createRoot }))
    vi.doMock('@/features/auth/msal/client', () => ({ initializeMsal }))
    vi.doMock('@/app/App', () => ({ App: () => <div>app</div> }))
    vi.doMock('@/app/providers', () => ({
      AppProviders: ({ children }: { children: ReactNode }) => <div>{children}</div>,
    }))

    await import('@/main')

    await waitFor(() => {
      expect(initializeMsal).toHaveBeenCalledOnce()
      expect(createRoot).toHaveBeenCalledWith(document.getElementById('root'))
      expect(appRender).toHaveBeenCalledOnce()
    })
  })
})
