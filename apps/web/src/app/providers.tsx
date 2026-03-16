import { MsalProvider } from "@azure/msal-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import type { PropsWithChildren } from "react";
import { msalInstance } from "@/features/auth/msal/client";

export function AppProviders({ children }: PropsWithChildren) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
          },
        },
      }),
  );

  return (
    <MsalProvider instance={msalInstance}>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </MsalProvider>
  );
}
