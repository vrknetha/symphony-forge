import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Integration tests run sequentially — they share a real database
    fileParallelism: false,
    globals: true,
    include: ['test/**/*.int-spec.ts'],
    // No coverage for integration tests — unit coverage covers the same code
    coverage: { enabled: false },
    // Long timeout for DB round-trips
    testTimeout: 30_000,
    hookTimeout: 30_000,
    // Load .env.test if present
    env: { NODE_ENV: 'test' },
  },
});
