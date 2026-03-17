import { useCallback, useEffect, useRef } from 'react'
import type { PropsWithChildren } from 'react'
import { useMsal } from '@azure/msal-react'
import { appEnv } from '@/config/env'
import { mockSessionUser } from '@/shared/lib/mock-data'
import type { AppRole, AuthUser } from '@/shared/types/models'
import { loginRequest } from '../msal/client'
import { useAuthStore } from '../store/use-auth-store'
import { AuthContext } from './auth-context'

function getRole(idTokenClaims: unknown): AppRole {
  if (!idTokenClaims || typeof idTokenClaims !== 'object' || !('roles' in idTokenClaims)) return 'MEMBER'
  const roles = (idTokenClaims as { roles?: unknown }).roles
  if (!Array.isArray(roles)) return 'MEMBER'
  return roles.some((role) => typeof role === 'string' && (role === 'ADMIN' || role === 'Admin'))
    ? 'ADMIN'
    : 'MEMBER'
}

function sameUser(currentUser: AuthUser | null, nextUser: AuthUser) {
  return currentUser?.id === nextUser.id && currentUser.email === nextUser.email && currentUser.name === nextUser.name && currentUser.role === nextUser.role
}

function toAuthUser(account: { idTokenClaims?: unknown; localAccountId: string; name?: string | null; username: string }) {
  return {
    email: account.username,
    id: account.localAccountId,
    name: account.name ?? account.username,
    role: getRole(account.idTokenClaims),
  } satisfies AuthUser
}

export function AuthProvider({ children }: PropsWithChildren) {
  const { accounts, inProgress, instance } = useMsal()
  const { clearUser, setUser, user } = useAuthStore()
  const mockBootstrapped = useRef(false)

  useEffect(() => {
    if (appEnv.useMocks) {
      if (!mockBootstrapped.current) {
        mockBootstrapped.current = true
        if (!user) setUser(mockSessionUser)
      }
      return
    }

    const activeAccount = instance.getActiveAccount() ?? accounts[0]
    if (activeAccount) {
      instance.setActiveAccount(activeAccount)
      const nextUser = toAuthUser(activeAccount)
      if (!sameUser(user, nextUser)) setUser(nextUser)
      return
    }

    if (user) clearUser()
  }, [accounts, clearUser, instance, setUser, user])

  const login = useCallback(async () => {
    if (appEnv.useMocks) return void setUser(mockSessionUser)
    await instance.loginRedirect(loginRequest)
  }, [instance, setUser])

  const logout = useCallback(async () => {
    clearUser()
    if (appEnv.useMocks) return
    await instance.logoutRedirect({ postLogoutRedirectUri: appEnv.azureRedirectUri })
  }, [clearUser, instance])

  return (
    <AuthContext.Provider
      value={{
        isAdmin: user?.role === 'ADMIN',
        isAuthenticated: user !== null,
        isLoading: !appEnv.useMocks && inProgress !== 'none' && user === null,
        login,
        logout,
        user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
