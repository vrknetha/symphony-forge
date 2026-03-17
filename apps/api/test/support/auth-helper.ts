/**
 * Mock JWT injection for integration tests.
 * See conventions/testing.md — Mock JWT Injection section.
 *
 * Never use real auth flows in tests.
 */
import * as jwt from 'jsonwebtoken';

// Must match TEST_JWT_SECRET in .env.test
const TEST_SECRET = process.env['TEST_JWT_SECRET'] ?? 'test-jwt-secret-do-not-use-in-prod';

export interface TestClaims {
  sub?: string;
  email?: string;
  name?: string;
  role?: 'ADMIN' | 'MEMBER';
  azureOid?: string;
  [key: string]: unknown;
}

export function mockJwt(claims: TestClaims = {}): string {
  return jwt.sign(
    {
      sub: claims.sub ?? 'user-test-123',
      email: claims.email ?? 'test@test.com',
      name: claims.name ?? 'Test User',
      role: claims.role ?? 'MEMBER',
      azureOid: claims.azureOid ?? 'azure-test-oid',
      ...claims,
    },
    TEST_SECRET,
    { expiresIn: '1h' },
  );
}

export function authHeader(claims: TestClaims = {}): Record<string, string> {
  return { Authorization: `Bearer ${mockJwt(claims)}` };
}

export function adminAuthHeader(): Record<string, string> {
  return authHeader({ role: 'ADMIN', sub: 'admin-test-123', email: 'admin@test.com' });
}
