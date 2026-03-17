import { createHash, randomBytes } from 'node:crypto';

const KEY_PREFIX_LENGTH = 8;

export function buildAgentKeyMaterial(): {
  hash: string;
  prefix: string;
  rawKey: string;
} {
  const rawKey = `sk_${randomBytes(24).toString('hex')}`;

  return {
    hash: createHash('sha256').update(rawKey).digest('hex'),
    prefix: rawKey.slice(0, KEY_PREFIX_LENGTH),
    rawKey,
  };
}

export function hashAgentKey(rawKey: string): string {
  return createHash('sha256').update(rawKey).digest('hex');
}
