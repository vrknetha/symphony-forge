/**
 * User test factory.
 * See conventions/testing.md — Test Factories section.
 */
import { faker } from '@faker-js/faker';
import type { User, Role } from '@prisma/client';

export function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: faker.string.uuid(),
    externalId: faker.string.uuid(),
    email: faker.internet.email(),
    name: faker.person.fullName(),
    role: 'MEMBER' as Role,
    createdAt: faker.date.recent(),
    updatedAt: faker.date.recent(),
    ...overrides,
  };
}

export function buildAdminUser(overrides: Partial<User> = {}): User {
  return buildUser({ role: 'ADMIN' as Role, ...overrides });
}
