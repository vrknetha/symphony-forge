import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      exclude: [
        'src/main.ts',
        'src/openapi.ts',
        'src/**/*.module.ts',    // NestJS module files are wiring — tested via integration
        'src/**/*.d.ts',
        'test/**',
        'prisma/**',
        'dist/**',
      ],
      include: ['src/**/*.ts'],
      provider: 'v8',
      reporter: ['text', 'lcov'],
      thresholds: {
        branches: 100,
        functions: 100,
        lines: 100,
        statements: 100,
      },
    },
    environment: 'node',
    globals: true,
    // Unit tests only — integration tests run separately
    include: ['src/**/*.spec.ts'],
    exclude: ['**/*.int-spec.ts', '**/*.e2e-spec.ts', 'dist/**'],
  },
});
