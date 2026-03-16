const defaultApiBaseUrl = "http://localhost:3000/api/v1";
const defaultRedirectUri = "http://localhost:5173";

export const appEnv = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl,
  azureAuthority:
    import.meta.env.VITE_AZURE_AUTHORITY ??
    "https://login.microsoftonline.com/common",
  azureClientId:
    import.meta.env.VITE_AZURE_CLIENT_ID ?? "placeholder-client-id",
  redirectUri: import.meta.env.VITE_AZURE_REDIRECT_URI ?? defaultRedirectUri,
  useMocks: import.meta.env.VITE_USE_MOCKS !== "false",
};
