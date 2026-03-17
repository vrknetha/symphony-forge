import { PrismaClient, Role } from '@prisma/client';

const prisma = new PrismaClient();

async function main(): Promise<void> {
  const admin = await prisma.user.upsert({
    create: {
      azureOid: 'azure-admin-seed',
      email: 'forge-admin@knacklabs.ai',
      name: 'Forge Admin',
      role: Role.ADMIN,
    },
    update: {
      name: 'Forge Admin',
      role: Role.ADMIN,
    },
    where: { email: 'forge-admin@knacklabs.ai' },
  });

  await prisma.project.upsert({
    create: {
      description: 'Seed project for local development.',
      name: 'Symphony Forge',
      ownerId: admin.id,
      slug: 'symphony-forge',
    },
    update: {
      description: 'Seed project for local development.',
    },
    where: { slug: 'symphony-forge' },
  });
}

main()
  .catch(async (error: unknown) => {
    process.stderr.write(`${String(error)}\n`);
    await prisma.$disconnect();
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
