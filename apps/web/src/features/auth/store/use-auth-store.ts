import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { AuthUser } from '@/shared/types/models'

interface AuthStore {
  clearUser: () => void
  setUser: (user: AuthUser | null) => void
  user: AuthUser | null
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      clearUser: () => set({ user: null }),
      setUser: (user) => set({ user }),
      user: null,
    }),
    {
      name: 'symphony-auth-session',
      partialize: ({ user }) => ({ user }),
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
)
