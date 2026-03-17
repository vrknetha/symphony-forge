/**
 * Project test factory.
 */
import { faker } from '@faker-js/faker';
import type { Project, ProjectStatus } from '@prisma/client';

export function buildProject(overrides: Partial<Project> = {}): Project {
  const name = overrides.name ?? faker.company.name();
  return {
    id: faker.string.uuid(),
    name,
    slug: overrides.slug ?? name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
    description: faker.lorem.sentence(),
    status: 'ACTIVE' as ProjectStatus,
    ownerId: faker.string.uuid(),
    deletedAt: null,
    createdAt: faker.date.recent(),
    updatedAt: faker.date.recent(),
    ...overrides,
  };
}
