/**
 * Database seed script.
 * Minimal local dev data — uses upsert so it's idempotent.
 * See conventions/database.md — Seed Scripts section.
 */
import { PrismaClient, Role } from '@prisma/client';

const prisma = new PrismaClient();

async function main(): Promise<void> {
  const admin = await prisma.user.upsert({
    where: { email: 'admin@dev.local' },
    create: {
      externalId: 'seed-admin-oid',  // placeholder — real value comes from OIDC `sub` claim
      email: 'admin@dev.local',
      name: 'Dev Admin',
      role: Role.ADMIN,
    },
    update: {
      name: 'Dev Admin',
      role: Role.ADMIN,
    },
  });

  await prisma.project.upsert({
    where: { slug: 'seed-project' },
    create: {
      name: 'Seed Project',
      slug: 'seed-project',
      description: 'Local dev seed project.',
      ownerId: admin.id,
    },
    update: {
      description: 'Local dev seed project.',
    },
  });
}

main()
  .catch(async (error: unknown) => {
    process.stderr.write(`Seed failed: ${String(error)}\n`);
    await prisma.$disconnect();
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
