import { registerAs } from '@nestjs/config';

export const appConfig = registerAs('app', () => ({
  apiPort: Number.parseInt(process.env.API_PORT ?? '3000', 10),
  cookieName: process.env.AUTH_COOKIE_NAME ?? 'symphony_forge_session',
  corsOrigins: (process.env.CORS_ORIGINS ?? 'http://localhost:5173').split(','),
  nodeEnv: process.env.NODE_ENV ?? 'development',
  serviceName: 'symphony-api',
  webBaseUrl: process.env.WEB_BASE_URL ?? 'http://localhost:5173',
}));
