/**
 * Document test factory.
 *
 * NOTE: The harness schema has no Document model by default.
 * This is a placeholder showing the factory pattern.
 * Replace with your project's actual domain models.
 */

// import { faker } from '@faker-js/faker';
// import type { Document } from '@prisma/client';
//
// export function buildDocument(overrides: Partial<Document> = {}): Document {
//   const title = overrides.title ?? faker.lorem.words(3);
//   return {
//     id: faker.string.uuid(),
//     title,
//     slug: overrides.slug ?? title.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
//     projectId: faker.string.uuid(),
//     createdById: faker.string.uuid(),
//     deletedAt: null,
//     createdAt: faker.date.recent(),
//     updatedAt: faker.date.recent(),
//     ...overrides,
//   };
// }
