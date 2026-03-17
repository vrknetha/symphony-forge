/**
 * Document test factory.
 */
import { faker } from '@faker-js/faker';
import type { Document, DocType } from '@prisma/client';

export function buildDocument(overrides: Partial<Document> = {}): Document {
  const title = overrides.title ?? faker.lorem.words(3);
  return {
    id: faker.string.uuid(),
    title,
    slug: overrides.slug ?? title.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
    docType: 'NOTES' as DocType,
    projectId: faker.string.uuid(),
    createdById: faker.string.uuid(),
    proofDocSlug: faker.string.uuid(),
    proofOwnerSecret: faker.string.alphanumeric(32),
    proofAccessToken: faker.string.alphanumeric(32),
    deletedAt: null,
    createdAt: faker.date.recent(),
    updatedAt: faker.date.recent(),
    ...overrides,
  };
}
