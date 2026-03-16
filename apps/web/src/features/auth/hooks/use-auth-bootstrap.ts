import { useEffect } from "react";
import { useMsal } from "@azure/msal-react";
import { appEnv } from "@/config/env";
import { mockUser } from "@/shared/lib/mock-data";
import { useAuthStore } from "../store/use-auth-store";

export function useAuthBootstrap() {
  const { accounts } = useMsal();
  const { setUser } = useAuthStore();

  useEffect(() => {
    if (accounts.length > 0) {
      const primary = accounts[0];
      setUser({
        email: primary.username,
        id: primary.localAccountId,
        name: primary.name ?? primary.username,
        role: "MEMBER",
      });
      return;
    }

    if (appEnv.useMocks) {
      setUser(mockUser);
    }
  }, [accounts, setUser]);
}
