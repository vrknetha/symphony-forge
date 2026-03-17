const defaultApiBaseUrl = 'http://localhost:3000/api/v1'
const defaultAuthority = 'https://login.microsoftonline.com/common'
const defaultRedirectUri = 'http://localhost:5173'
const defaultScopes = ['openid', 'profile', 'email']
const envScopes = import.meta.env.VITE_AZURE_SCOPES as string | undefined

function parseScopes(scopes: string | undefined) {
  if (!scopes) {
    return defaultScopes
  }

  return scopes
    .split(',')
    .map((scope) => scope.trim())
    .filter((scope) => scope.length > 0)
}

export const appEnv = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl,
  azureAuthority: import.meta.env.VITE_AZURE_AUTHORITY ?? defaultAuthority,
  azureClientId: import.meta.env.VITE_AZURE_CLIENT_ID ?? 'local-dev-client-id',
  azureRedirectUri: import.meta.env.VITE_AZURE_REDIRECT_URI ?? defaultRedirectUri,
  azureScopes: parseScopes(envScopes),
  useMocks: import.meta.env.VITE_USE_MOCKS !== 'false',
}
