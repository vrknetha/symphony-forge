import { PublicClientApplication } from "@azure/msal-browser";
import { appEnv } from "@/config/env";

export const msalInstance = new PublicClientApplication({
  auth: {
    authority: appEnv.azureAuthority,
    clientId: appEnv.azureClientId,
    redirectUri: appEnv.redirectUri,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
});
