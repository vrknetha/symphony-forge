import { useMsal } from "@azure/msal-react";
import { appEnv } from "@/config/env";
import { mockUser } from "@/shared/lib/mock-data";
import { useAuthStore } from "../store/use-auth-store";

export function useLogin() {
  const { instance } = useMsal();
  const { setUser } = useAuthStore();

  return async () => {
    if (appEnv.useMocks) {
      setUser(mockUser);
      return;
    }

    await instance.loginRedirect({
      scopes: ["openid", "profile", "email"],
    });
  };
}
