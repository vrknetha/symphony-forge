const EMAIL_PATTERN =
  /([a-zA-Z0-9._%+-]{2})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g;
const PHONE_PATTERN =
  /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;
const SECRET_KEYS = ['authorization', 'cookie', 'password', 'secret', 'token'];
const NAME_KEYS = ['name', 'firstname', 'lastname', 'fullname'];

export function maskPii(value: string): string {
  return value
    .replace(EMAIL_PATTERN, '$1***@$2')
    .replace(PHONE_PATTERN, (match) => `***${match.slice(-4)}`);
}

export function sanitizeObject(value: unknown): unknown {
  if (typeof value === 'string') {
    return maskPii(value);
  }

  if (Array.isArray(value)) {
    return value.map((item) => sanitizeObject(item));
  }

  if (value && typeof value === 'object') {
    return Object.entries(value).reduce<Record<string, unknown>>(
      (accumulator, [key, item]) => {
        const loweredKey = key.toLowerCase();

        if (SECRET_KEYS.includes(loweredKey)) {
          accumulator[key] = '[REDACTED]';
          return accumulator;
        }

        if (NAME_KEYS.includes(loweredKey)) {
          accumulator[key] = '[PII_REMOVED]';
          return accumulator;
        }

        accumulator[key] = sanitizeObject(item);
        return accumulator;
      },
      {},
    );
  }

  return value;
}
