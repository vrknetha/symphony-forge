import { registerAs } from '@nestjs/config';

export const authConfig = registerAs('auth', () => ({
  callbackUrl:
    process.env.AZURE_AD_CALLBACK_URL ??
    'http://localhost:3000/auth/callback',
  clientId: process.env.AZURE_AD_CLIENT_ID ?? '',
  clientSecret: process.env.AZURE_AD_CLIENT_SECRET ?? '',
  redirectUri: process.env.AZURE_AD_REDIRECT_URI ?? 'http://localhost:5173',
  scopes: (process.env.AZURE_AD_SCOPES ?? 'openid,profile,email').split(','),
  tenantId: process.env.AZURE_AD_TENANT_ID ?? 'common',
}));
