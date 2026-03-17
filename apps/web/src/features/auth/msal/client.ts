import {
  InteractionRequiredAuthError,
  PublicClientApplication,
} from '@azure/msal-browser'
import { appEnv } from '@/config/env'

export const msalInstance = new PublicClientApplication({
  auth: {
    authority: appEnv.azureAuthority,
    clientId: appEnv.azureClientId,
    redirectUri: appEnv.azureRedirectUri,
  },
  cache: {
    cacheLocation: 'sessionStorage',
  },
})

export const loginRequest = {
  scopes: appEnv.azureScopes,
}

export async function initializeMsal() {
  await msalInstance.initialize()
  const result = await msalInstance.handleRedirectPromise()
  const activeAccount = result?.account ?? msalInstance.getAllAccounts()[0]

  if (activeAccount) {
    msalInstance.setActiveAccount(activeAccount)
  }
}

export async function acquireAccessToken() {
  if (appEnv.useMocks) {
    return null
  }

  const account = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0]

  if (!account) {
    throw new Error('No authenticated account is available.')
  }

  try {
    const response = await msalInstance.acquireTokenSilent({
      account,
      scopes: appEnv.azureScopes,
    })
    return response.accessToken
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      throw new Error('Authentication is required before calling the API.')
    }

    throw error
  }
}
