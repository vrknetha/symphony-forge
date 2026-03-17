import { registerAs } from '@nestjs/config';
import { PROOF_PROXY_TIMEOUT_MS } from '@symphony/shared';

export const proofConfig = registerAs('proof', () => ({
  apiKey: process.env.PROOF_SDK_API_KEY ?? '',
  baseUrl: process.env.PROOF_SDK_BASE_URL ?? 'http://localhost:4000',
  timeoutMs: PROOF_PROXY_TIMEOUT_MS,
}));
