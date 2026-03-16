import { create } from "zustand";
import type { AuthUser } from "@/shared/types/models";

interface AuthStore {
  clearUser: () => void;
  setUser: (user: AuthUser | null) => void;
  user: AuthUser | null;
}

export const useAuthStore = create<AuthStore>((set) => ({
  clearUser: () => set({ user: null }),
  setUser: (user) => set({ user }),
  user: null,
}));
