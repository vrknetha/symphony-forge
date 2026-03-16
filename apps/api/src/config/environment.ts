import { registerAs } from '@nestjs/config';

const DEFAULT_API_PORT = 3000;
const DEFAULT_ALLOWED_ORIGINS = 'http://localhost:5173';
const DEFAULT_PROOF_BASE_URL = 'http://localhost:4000';

function readRequired(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function readOptional(name: string, fallback: string): string {
  return process.env[name] ?? fallback;
}

function readPort(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  if (Number.isNaN(parsed)) {
    throw new Error(`Invalid numeric environment variable: ${name}`);
  }
  return parsed;
}

export const environment = registerAs('env', () => ({
  apiPort: readPort('API_PORT', DEFAULT_API_PORT),
  webOrigin: readOptional('AZURE_AD_REDIRECT_URI', DEFAULT_ALLOWED_ORIGINS),
  allowedOrigins: readOptional('CORS_ORIGINS', DEFAULT_ALLOWED_ORIGINS)
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean),
  azureTenantId: readRequired('AZURE_AD_TENANT_ID'),
  azureClientId: readRequired('AZURE_AD_CLIENT_ID'),
  azureClientSecret: readRequired('AZURE_AD_CLIENT_SECRET'),
  azureCallbackUrl: readRequired('AZURE_AD_CALLBACK_URL'),
  proofBaseUrl: readOptional('PROOF_SDK_BASE_URL', DEFAULT_PROOF_BASE_URL),
  proofApiKey: readRequired('PROOF_SDK_API_KEY'),
  appEncryptionKey: readRequired('APP_ENCRYPTION_KEY'),
}));

export type AppEnvironment = ReturnType<typeof environment>;
