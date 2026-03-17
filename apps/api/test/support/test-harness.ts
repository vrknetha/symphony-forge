/**
 * Integration test harness.
 * See conventions/testing.md — Integration Tests section.
 */
import { INestApplication, ValidationPipe } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { PrismaService } from '../../src/prisma/prisma.service';

// Lazily imported to avoid coupling at import time
let appModule: typeof import('../../src/app.module');

export async function createTestApp(): Promise<INestApplication> {
  appModule = await import('../../src/app.module');

  const module: TestingModule = await Test.createTestingModule({
    imports: [appModule.AppModule],
  }).compile();

  const app = module.createNestApplication();

  // Mirror main.ts bootstrap (must stay in sync)
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  await app.init();
  return app;
}

/**
 * Transaction rollback wrapper.
 * Rolls back every database write after each test — no truncation, no ordering issues.
 *
 * Usage:
 *   const tx = withTransaction(app);
 *   it('...', () => tx.run(async (prisma) => { ... }));
 */
export function withTransaction(app: INestApplication) {
  const prisma = app.get(PrismaService);

  return {
    async run(fn: (prisma: PrismaService) => Promise<void>): Promise<void> {
      await (prisma.$transaction as Function)(async (tx: PrismaService) => {
        // Temporarily swap prisma methods with the transaction client
        const originalMethods = Object.getOwnPropertyNames(
          Object.getPrototypeOf(prisma),
        ).filter((k) => k.startsWith('$') || (tx as any)[k]);

        const saved: Record<string, unknown> = {};
        for (const key of Object.keys(tx as object)) {
          saved[key] = (prisma as any)[key];
          (prisma as any)[key] = (tx as any)[key];
        }

        try {
          await fn(prisma);
        } finally {
          // Restore
          for (const [key, val] of Object.entries(saved)) {
            (prisma as any)[key] = val;
          }
          // Force rollback
          throw new Error('__ROLLBACK__');
        }
      }).catch((e: Error) => {
        if (e.message !== '__ROLLBACK__') throw e;
      });
    },
  };
}
