import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useMsal } from '@azure/msal-react'

vi.mock('@azure/msal-react', () => ({
  useMsal: vi.fn(),
}))

type MsalInstance = {
  getActiveAccount: ReturnType<typeof vi.fn>
  loginRedirect: ReturnType<typeof vi.fn>
  logoutRedirect: ReturnType<typeof vi.fn>
  setActiveAccount: ReturnType<typeof vi.fn>
}

const mockedUseMsal = vi.mocked(useMsal)

beforeEach(() => {
  sessionStorage.clear()
  vi.clearAllMocks()
  vi.resetModules()
})

function createInstance(): MsalInstance {
  return {
    getActiveAccount: vi.fn(() => null),
    loginRedirect: vi.fn(() => Promise.resolve()),
    logoutRedirect: vi.fn(() => Promise.resolve()),
    setActiveAccount: vi.fn(),
  }
}

async function renderProvider() {
  const auth = await import('@/features/auth/hooks/use-auth')
  const { AuthProvider } = await import('@/features/auth/providers/AuthProvider')
  const { useAuthStore } = await import('@/features/auth/store/use-auth-store')

  useAuthStore.setState({ user: null })
  const Consumer = () => {
    const value = auth.useAuth()
    return (
      <div>
        <p>{value.user?.name ?? 'guest'}</p>
        <p>{value.user?.role ?? 'NONE'}</p>
        <p>{value.isLoading ? 'loading' : 'idle'}</p>
        <button onClick={() => void value.login()}>login</button>
        <button onClick={() => void value.logout()}>logout</button>
      </div>
    )
  }

  render(
    <AuthProvider>
      <Consumer />
    </AuthProvider>,
  )

  return { useAuthStore }
}

describe('AuthProvider', () => {
  it('hydrates and clears the mock session without redirect calls', async () => {
    const instance = createInstance()
    mockedUseMsal.mockReturnValue({ accounts: [], inProgress: 'none', instance } as never)

    const { useAuthStore } = await renderProvider()
    await screen.findByText('Ravi Kiran')
    expect(screen.getByText('ADMIN')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'logout' }))
    await waitFor(() => expect(screen.getByText('guest')).toBeInTheDocument())
    expect(useAuthStore.getState().user).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'login' }))
    await screen.findByText('Ravi Kiran')
    expect(instance.loginRedirect).not.toHaveBeenCalled()
    expect(instance.logoutRedirect).not.toHaveBeenCalled()
  })

  it('maps the active Azure account and delegates redirects when mocks are disabled', async () => {
    const instance = createInstance()
    const account = {
      idTokenClaims: { roles: ['Admin'] },
      localAccountId: 'user-1',
      name: 'Ravi Kiran',
      username: 'ravi@knacklabs.ai',
    }

    mockedUseMsal.mockReturnValue({ accounts: [account], inProgress: 'none', instance } as never)
    vi.doMock('@/config/env', () => ({
      appEnv: {
        azureRedirectUri: 'http://localhost:5173',
        useMocks: false,
      },
    }))

    await renderProvider()
    await screen.findByText('Ravi Kiran')
    expect(screen.getByText('ADMIN')).toBeInTheDocument()
    expect(instance.setActiveAccount).toHaveBeenCalledWith(account)

    fireEvent.click(screen.getByRole('button', { name: 'login' }))
    fireEvent.click(screen.getByRole('button', { name: 'logout' }))

    await waitFor(() => {
      expect(instance.loginRedirect).toHaveBeenCalledOnce()
      expect(instance.logoutRedirect).toHaveBeenCalledWith({
        postLogoutRedirectUri: 'http://localhost:5173',
      })
    })
  })

  it('clears stale state and reports loading while Azure auth is in progress', async () => {
    const instance = createInstance()
    mockedUseMsal.mockReturnValue({ accounts: [], inProgress: 'startup', instance } as never)
    vi.doMock('@/config/env', () => ({
      appEnv: {
        azureRedirectUri: 'http://localhost:5173',
        useMocks: false,
      },
    }))

    const { useAuthStore } = await import('@/features/auth/store/use-auth-store')
    useAuthStore.setState({
      user: {
        email: 'maya@knacklabs.ai',
        id: 'user-2',
        name: 'Maya Chen',
        role: 'MEMBER',
      },
    })

    await renderProvider()
    await waitFor(() => expect(screen.getByText('guest')).toBeInTheDocument())
    expect(screen.getByText('loading')).toBeInTheDocument()
  })
})
