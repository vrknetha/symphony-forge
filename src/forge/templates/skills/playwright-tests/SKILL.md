---
name: playwright-tests
description: "Follow when writing or changing Playwright browser tests or their CI, including fixtures, sign-in, waits, workers and sharding."
---

# Playwright tests

Folder layout, per app, under e2e/:
- fixtures/: base.ts exports one `test` and `expect`, built with mergeTests from typed TestFixtures and WorkerFixtures. Specs import only this file.
- setup/: a setup project that signs in once per role and saves storageState.
- pages/: page objects per screen, grouped by area, provided as fixtures.
- api/: API and reset helpers, provided as fixtures.
- data/: test data.
- matchers/: a few custom matchers.
- specs/: tests grouped by area.

Rules:
1. Worker-scoped fixtures ({ scope: 'worker' }) for expensive setup, such as a database per worker: reset between tests, tear down after.
2. Option data fixtures ({ option: true }) for default data, overridden only with test.use at file or describe level, never inside a test body. Option fixture types are not optional.
3. A createContext fixture for tests with several people (for example host, guest, admin): one browser context each; every context is tracked and closed in teardown.
4. Sign in through storageState from the setup project, not through the UI in each test.
5. Custom matchers must retry (expect(...).toPass() inside, or use built-ins such as toContainText(/x/i)). Give clear failure messages and declare them on PlaywrightTest.Matchers. Keep them few.
6. Locators: getByRole and getByLabel. Use waitForURL, not waitForNavigation. No fixed waits.
7. The config reads WORKERS from the environment, parsed as a number. WORKERS defaults to the available CPUs divided by the CPUs each browser needs. No hard-coded workers: 1. RETRIES can be read as a number for local debugging, but defaults to 0. CI never sets retries above 0.
8. CI: a shard matrix built from an input, with fail-fast: false; the blob reporter plus one merge-reports job for a single HTML report. workflow_dispatch inputs (shards, project, grep) pass through env and are quoted, never placed raw in a shell line. Desktop only on pull requests; all projects nightly.
9. Environment choice (BASE_URL) only when a repo has more than one environment.
10. Seed the database directly only for the initial fresh data (one base seed per worker). Every other piece of test setup goes through the app's real APIs (for example the admin API, the user API and webhooks), so setup also tests those APIs. Use a test-only route only for what no real API can do (for example moving the clock), and say why in the helper.
