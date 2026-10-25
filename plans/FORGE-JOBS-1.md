# Background jobs for client apps, with no Redis

9 parts · Risks: none one-way · New moving parts: a Postgres job queue and a worker process in both starters

## What changes for you

- A new client app gets a background job queue that keeps its jobs in the app's own Postgres
  database. The app needs no Redis and no other queue server. The NestJS starter uses pg-boss and
  the Python starter uses Procrastinate.
- A worker process runs the jobs. It comes from the same code as the API and starts next to the
  API in Docker Compose.
- Invite emails and CSV exports run as jobs. The web request saves the record and adds the job,
  and the worker sends the email or makes the file.
- The Export CSV button asks for the file, shows that the file is in preparation, and downloads
  it when the worker has made it.
- A job and its record are saved together. When the save fails, no job stays behind.
- A job that fails tries again after a longer wait each time. A job can run on a schedule: each
  night the app removes export files older than seven days. Each job has a time limit. A job that
  runs two times for the same record has the same result as one run.
- Admins get a Jobs screen that lists the failed jobs of their organisation, with a Retry button.
  Members do not see it.
- The API and the worker each answer two health checks: one that says the process runs, and one
  that says it is ready. The ready check fails when the database is down.
- The database rules tell the agent how to add a job: in the same transaction as its record,
  keyed by the record id, with a time limit and no long transaction.
- Existing apps keep their code. On upgrade they get the rules and a guide that tells how to add
  the worker.

Design: docs/design/FORGE-JOBS-1/ (TREE)

## Why

Client apps need background work such as invite emails and CSV exports, with retries and
schedules. The starters have no worker. They send invites and make CSV files inside the web
request, so a slow mail provider or a large table makes the request slow, and a failed email is
lost. A Redis queue such as BullMQ adds one more server to run and pay for. On 25 October 2026 the
owner chose a Postgres queue in both starters from the first day, a worker from the same code, and
jobs saved in the same transaction as their data.

## Done when

1. **A new app from either starter has a worker in Docker Compose, from the same code as the API, that sends invite emails and makes CSV exports from jobs in Postgres, with no Redis; the web request no longer sends the email or makes the file.**
2. **A job is added in the same transaction as its record, and a rolled-back save leaves no job.**
3. **A failed job tries again after longer and longer waits, a scheduled job runs on its cron schedule, each job has a time limit, and a second run of a job for the same record changes nothing.**
4. **An admin sees the failed jobs of their organisation on the Jobs screen, and Retry runs one again; a member cannot see the screen or retry a job.**
5. **The API and the worker each answer a liveness and a readiness check, and the readiness check fails while the database is down.**
6. **The database skill and the guides have the job rules and the steps to add the worker, and an existing app's code is unchanged after upgrade.**

## Risks

<!-- Each one-way step: deleting data, a destructive migration, a new vendor. -->

Risks: none one-way. Each part reverts with its pull request. The new migrations change only the
starters, which a new app copies at set-up; no existing app gets them.

Trade-off: the invite email job keeps the invite link in the job's data until the queue removes
the finished job (after about seven days in both libraries). The link works for seven days only,
and the worker sends it only while it is the newest link for that invite. The other way is to
make the link in the worker, which needs a change to the invite table.

Trade-off: the export file is kept in a database table, not in file storage. This is good for the
constitution's size of app. A later story moves files to object storage when a table passes about
50,000 rows.

Trade-off: the Jobs screen shows the kind of job, its record, its attempts and when it failed. It
does not show the error text, because error text can hold personal data. The worker's logs keep
the kind of error.

Trade-off: the nightly clean-up job belongs to no organisation, so a failed clean-up shows in the
worker's logs and not on a Jobs screen.

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

Each new test file starts with `STORY = "FORGE-JOBS-1"`. Each test runs the forge command or, for
the starter's own behaviour, reads the starter's files or runs its own commands, and never imports
forge. One test per Done-when rule, named `test_<n>_...`. The starter's behaviour is proven by its
own live cases, as FORGE-DEFAULTS-1 does: Supertest cases in `apps/api/test/*.e2e-spec.ts` and
Playwright flows in `apps/web/e2e/*.spec.ts` against `compose.test.yml`, and the Python starter's
HTTP cases in `apps/api/tests/test_*.py`, named from the TypeScript case names as FORGE-DEFAULTS-1's
"Python API side" says. Each part's pytest wrapper requires its case names from `live_run`
(tests/test_starter_tree.py) and `live_python_starter` (tests/test_python_starter.py) under the
existing `LIVE` switch, with `@pytest.mark.platform` and `@pytest.mark.timeout(1800)`.
"Adopted case" means the `tests/fixtures/adopted-v1.2.2/client` repo moved to this release, as
`test_4` in tests/test_defaults_soft_delete.py sets it up.

All paths under `starter/` mean `src/forge/templates/starter/`, and `starter-python/` means
`src/forge/templates/starter-python/`.

No extra guards for unlikely races or security edge cases (owner rule). No Redis, BullMQ, Celery,
RQ or other queue server anywhere in this story.

**Plan against the merged starters.** The starter parts start after FORGE-DATABASE-1's PG18,
COLUMNS and COLUMNSPY parts (Postgres 18, `uuidv7()` ids, text status with a named check,
timestamptz). New tables follow the database skill that FORGE-DATABASE-1/SKILL ships. Where a
path or a migration name below differs from the merged tree, follow the merged tree and keep the
order: this story's migrations come after FORGE-DATABASE-1's.

### Same-transaction enqueue (checked in the libraries' docs, 25 Oct 2026)

- **pg-boss can do it with Prisma.** pg-boss 12 has a Prisma adapter: `send(name, data, { db:
  fromPrisma(tx) })` inside `prisma.$transaction(async (tx) => ...)`. When the Prisma transaction
  rolls back, the job rolls back too. It needs Prisma 7 with `@prisma/adapter-pg`, which the
  starter already uses (Prisma 7.10.1, `PrismaPg` in `PrismaService`). So no Graphile Worker.
- **Procrastinate can do it with the starter's SQLAlchemy.** `task.configure(connection=conn)
  .defer(...)` runs the job insert on a connection you give it, inside your transaction, and you
  commit. The sync psycopg connector takes a `psycopg.Connection`. Procrastinate's own SQLAlchemy
  connector is for psycopg2 only, and the Python starter uses SQLAlchemy 2.1 on psycopg 3, so the
  API passes the psycopg connection under the request's session:
  `db.connection().connection.driver_connection`. The API never opens `job_app`, so its sync
  defer uses the sync connector. The worker sees the job after the commit.
- The rollback case in item 2 proves both in the live runs. Sources are in Notes.

### Shared names

The part named first owns each name; later parts use it and list that part under After.

- **Job kinds (pinned by QUEUE).** Three kinds, the same name in both starters: `invite-email`,
  `csv-export` and `export-cleanup`. In pg-boss each is a queue; in Procrastinate each is a task
  with `name=` set to that string. Job data: TypeScript `{ organisationId, inviteId, email,
  inviteUrl }` and `{ organisationId, exportId }`; Python the same keys in snake_case.
  `export-cleanup` has no data.
- **Job policy (pinned by QUEUE).** Each kind has: 4 retries; exponential back-off from a base
  wait of 30 seconds, or 1 second when `APP_ENV` is `test`, with at most 1 hour between tries; a
  time limit of 60 seconds for `invite-email` and 300 seconds for `csv-export` and
  `export-cleanup`. pg-boss: `createQueue` with `retryLimit: 4, retryDelay, retryBackoff: true,
  retryDelayMax: 3600, expireInSeconds`. Procrastinate: `retry=RetryStrategy(max_attempts=5,
  exponential_wait=<base>)` and `asyncio.timeout(<limit>)` around the task body. A ponytail comment
  at the policy says the test wait is short so the live run stays fast.
- **TypeScript jobs core (pinned by QUEUE)**, `starter/libs/core/src/jobs/`, exported from
  `@app/core`: `JobsModule.forRoot({ worker: boolean })` (global) and `JobsService` with
  `send(kind, data, tx)` (always inside the caller's Prisma transaction, through `{ db:
  fromPrisma(tx) }`), `handle(kind, handler: (data, signal: AbortSignal) => Promise<void>)` (each
  module calls it from `onModuleInit`; only the worker starts `boss.work` for it), `schedule(kind,
  cron)` (only the worker applies it), and later `findFailed(organisationId)` and `retry(id,
  organisationId)` (FAILEDJOBS). The API's pg-boss instance has `supervise: false, schedule:
  false`; the worker's uses the defaults. `start()` installs the `pgboss` schema, so Prisma's
  migrations do not hold it, and Prisma's drift check (which reads only `public`) does not see it.
  Both processes create the three queues at start. The handler gets pg-boss's `signal`, which
  aborts at the time limit.
- **Python jobs core (pinned by QUEUEPY)**, `starter-python/apps/api/app/core/jobs.py`, exported
  from `app.core`: `job_app` (a Procrastinate `App` on `PsycopgConnector`, with `import_paths` of
  each module's `tasks` file), `job_task(name, time_limit)` (the task decorator with the policy
  above), `defer(db, task, **data)` (the `configure(connection=...)` call above; the caller
  commits), and later `failed_jobs(db, organisation_id)` and `retry_job(db, job_id,
  organisation_id)` (FAILEDJOBS). Revision `0009_jobs` (down revision: the last one that
  FORGE-DATABASE-1 adds) runs the schema SQL that the installed Procrastinate ships
  (`procrastinate/sql/schema.sql`). `migrations/env.py` gets an `include_object` that skips names
  that start with `procrastinate_`, so `alembic check` passes. A ponytail comment says a
  Procrastinate upgrade adds its migration scripts as new revisions.
- **Worker entry (pinned by QUEUE, matched by QUEUEPY).** TypeScript
  `starter/apps/api/src/worker.ts`: `NestFactory.createApplicationContext(WorkerModule)`, so no
  controller serves HTTP, with `JobsModule.forRoot({ worker: true })`, then a `node:http` server
  on `PORT` that answers only the two health paths. Root script `start:worker` (`node
  apps/api/dist/worker.js`). `JsonLogger` takes a service name, and the worker logs as `worker`.
  Python `starter-python/apps/api/app/worker.py`: `worker_app`, a FastAPI app with only the two
  health routes, whose lifespan opens `job_app` and runs `run_worker_async` as a task; started
  with `uv run --no-sync uvicorn app.worker:worker_app --host 0.0.0.0 --port 3000`.
- **Worker log lines (pinned by QUEUE).** `Job started`, `Job finished` and `Job failed`, each
  with `{ kind, recordId, attempt }` (`recordId` is the invite or export id, or null), and at
  worker start `Job schedule registered` with `{ kind, cron }`. No job data and no error text in
  the context; `Job failed` adds the error's class name only.
- **Compose (pinned by QUEUE).** Each `compose.test.yml` gets a `worker` service: `build: .`, the
  API's environment, `command` the worker start above, `ports:
  ["127.0.0.1:${WORKER_TEST_PORT:-3002}:3000"]`, `depends_on: api: condition: service_healthy`
  (the API runs the migrations), and a healthcheck on `/health/ready`. `scripts/test.mjs` sets
  `WORKER_TEST_PORT` to a free port and `WORKER_TEST_URL`. The Dockerfile does not change.
- **Health (pinned by QUEUE).** `GET /health` stays as it is (the deploy contract). New:
  `GET /health/live` gives 200 with the same body as `/health` and reads no database.
  `GET /health/ready` runs `SELECT 1` with a 2-second limit and gives 200 with that body, or 503
  with `{ code: 'NOT_READY', message: 'The database is not reachable.', details: null }`. The
  worker answers the same two paths. Both are outside the `api/v1` prefix and the throttler, as
  `/health` is.
- **Exports (pinned by EXPORTJOBS).** Module `libs/jobs` (`@app/jobs`, tag `type:module`), wired
  as FORGE-DEFAULTS-1's module list says, with schema `apps/api/prisma/schema/jobs.prisma`:
  `Export { id, organisationId, requestedByAccountId, kind ('projects' | 'members' | 'history'),
  status ('pending' | 'ready'), fileName, content (text, null until ready), createdAtUtc,
  updatedAtUtc }`, kind and status as text with named checks, an index on `(organisationId,
  createdAtUtc)`. `ExportsService.request(account, kind)` creates the row and sends `csv-export`
  in one transaction. `ExportsService.register(kind, build: (organisationId) => Promise<{
  fileName: string; csv: string }>)`: each owning module registers its builder from
  `onModuleInit`, so `@app/jobs` imports no other module. The `csv-export` handler skips an export
  that is already `ready` (so a second run changes nothing), reads the rows with the builder
  outside a transaction, then sets `content` and `ready` in one short update. `export-cleanup`
  (cron `0 3 * * *`, UTC) deletes exports older than 7 days; the table has no `deletedAtUtc`, so
  this is a hard delete of temporary data. `csv.ts` splits into `buildCsv(columns, rows): string`
  and `sendCsvFile(response, fileName, body)`; `text/csv` stays only in `csv.ts`. Module graph:
  projects, organisations and history use `@app/jobs`; `@app/jobs` uses only core and shared.
- **Export API (pinned by EXPORTJOBS).** `POST /api/v1/projects/export`, `POST
  /api/v1/members/export` and `POST /api/v1/history/export` (admin only, as its GET is today) give
  `202 { id, status: 'pending' }`. `GET /api/v1/exports/:id` gives `{ id, status, fileName }`, and
  `GET /api/v1/exports/:id/download` sends the file; both answer only the account that asked for
  it in its organisation, else `404 EXPORT_NOT_FOUND` ("This export was not found."). A download
  before `ready` gives `409 EXPORT_NOT_READY` ("This export is not ready yet."). The old `GET
  /<list>/export` routes stay until EXPORTWEB removes them.
- **Failed jobs API (pinned by FAILEDJOBS).** `GET /api/v1/jobs/failed`, admin only, gives `{
  items: { id, kind, recordId, attempts, failedAtUtc }[] }`, newest first, only jobs whose data
  has the caller's organisation. pg-boss: `findJobs(kind, { data: { organisationId } })` for
  `invite-email` and `csv-export`, keeping `state === 'failed'`. Python: one `text()` query on
  `procrastinate_jobs` with `status = 'failed'` and `args->>'organisation_id'`, with the time of
  the job's last event, in `app/core/jobs.py`. `POST /api/v1/jobs/:id/retry`, admin only, gives
  `202 { id }`, or `404 JOB_NOT_FOUND` ("This failed job was not found.") for a job of another
  organisation or a job that is not failed. pg-boss `retry(kind, id)`; Procrastinate
  `retry_job_by_id(id, retry_at=now)`.
- **Test helpers (pinned by QUEUE).** `logEvents(service)` in both helper files takes `'api' |
  'production-api' | 'worker'`. New `waitForLogEvent(service, message, match, timeoutMs =
  20_000)` polls `logEvents` and returns the first new matching line. `sendJob(kind, data)` (API
  test helpers only) runs `docker compose -f compose.test.yml exec -T worker node -e ...` with
  pg-boss `send`. The Python test helper runs `uv run --no-sync procrastinate
  --app=app.core.jobs.job_app defer <task> '<json>'` in the worker container.

### Done-when details

1. A worker from the same code runs invite emails and CSV exports (QUEUE, QUEUEPY, INVITEJOBS,
   EXPORTJOBS, EXPORTJOBSPY, EXPORTWEB).
   - Dependencies: `pg-boss` at the 12.x release current at build time, pinned exactly in
     `starter/package.json` and the lockfile; `procrastinate` at the 3.x release current at build
     time (3.10.0 when planned), pinned in `starter-python/apps/api/pyproject.toml` and `uv.lock`.
     The starter's API is CommonJS; Node 24 loads an ES-module-only pg-boss through `require`, and
     the build proves it.
   - Invites (INVITEJOBS, both APIs): `invite()` keeps the `422 MAIL_NOT_CONFIGURED` check in the
     request (Python moves it from `send_invite` into a `MailProvider.configured()` check before
     the save). Then one transaction holds the invite upsert and the `invite-email` job (TS:
     `prisma.$transaction`; Python: `defer` before `db.commit()`). The history record stays where
     it is. The `invite-email` handler (in the organisations module) skips an invite whose token
     hash no longer matches the link (a newer invite replaced it) or that has expired; else it
     calls `MailProvider.sendInvite`. So the `Invite link created for local mail` line now comes
     from the worker. `invite()` in `apps/api/test/helpers.ts`, `inviteUrlsSince` in
     `apps/web/e2e/helpers.ts` and the Python test helper read it with `waitForLogEvent('worker',
     ...)`; join.spec, members.spec and history.spec change only that call.
   - API cases in the new `apps/api/test/jobs.e2e-spec.ts`: `the worker sends the invite email from
     a job` (INVITEJOBS: the invite answers 201, then the worker logs the link with the invite's
     `recordId`); `the worker makes the CSV export from a job` (EXPORTJOBS: `POST
     /projects/export` gives 202 `pending`; after `Job finished` the status is `ready` and the
     download is the projects CSV with its header row).
   - EXPORTWEB: one `ExportCsvButton({ path })` in `apps/web/src/components/` posts, shows the
     pending state, polls `GET /api/v1/exports/:id` each second for up to 60 seconds, then starts
     the download from `/api/v1/exports/:id/download`. After 60 seconds it says that the export
     takes longer and that an admin can see failed jobs on the Jobs screen; the texts come from
     the design. The three list pages use it in place of their `<a href=... download>`. Both APIs
     drop the old `GET /<list>/export` routes and their cases. The flow `Export CSV downloads the
     projects list` in `formats.spec.ts` keeps its name and waits for the download.
     `tests/test_defaults_formats.py::test_4` checks that every table page renders
     `<ExportCsvButton` in place of the `href` regex, and its `CSV_API_CASES` follow the export
     cases.
   - Test (new repo): `tests/test_jobs_worker.py::test_1_a_worker_from_the_same_code_runs_invites_and_exports`,
     parameters `react` and `python`: after `forge init --starter <kind>`, `compose.test.yml` has a
     `worker` service with `build: .` and the worker command; no file in the app names `redis`,
     `bullmq`, `ioredis`, `celery` or `rq` as a dependency; under `LIVE` the two cases pass in both
     live runs and the download flow passes. The existing-repo side is item 6's adopted case.
2. Same-transaction enqueue (INVITEJOBS).
   - API case `a rolled-back invite leaves no job`: `psql` creates a `CONSTRAINT TRIGGER ...
     DEFERRABLE INITIALLY DEFERRED` on `"Invite"` that raises for one fresh email, so the error
     comes at commit, after the job insert. The invite answers 500. `psql` then counts 0 rows in
     `pgboss.job` (Python: `procrastinate_jobs`) whose data `email` is that email, and no invite
     row for it. As a control, a normal invite in the same case leaves exactly one job. The
     trigger is dropped in a `finally`. Python case `test_a_rolled_back_invite_leaves_no_job`.
   - Export requests use the same `send(..., tx)` and `defer` path, so no second rollback case.
   - Test (new repo): `tests/test_jobs_worker.py::test_2_a_rolled_back_save_leaves_no_job` requires
     both cases.
3. Retries, schedule, time limit and second run (QUEUE, QUEUEPY, EXPORTJOBS, EXPORTJOBSPY,
   FAILEDJOBS).
   - Case `each job kind has its time limit` (QUEUE): `psql` reads `name, expire_seconds,
     retry_limit, retry_backoff` from `pgboss.queue` for the three kinds and finds the policy.
     Python case `test_each_job_kind_has_its_time_limit` (QUEUEPY): the three tasks have their
     limits, and `job_task`'s wrapper, run in-process on a coroutine that sleeps past a 0.1-second
     limit, raises `TimeoutError`.
   - Case `a second run of an export job changes nothing` (EXPORTJOBS): after an export is `ready`,
     `psql` reads its `updatedAtUtc` and content; `sendJob('csv-export', { organisationId, exportId
     })`; after the second `Job finished` for that `recordId`, both are the same.
   - Case `the export clean-up runs on its schedule and removes old exports` (EXPORTJOBS): the
     worker logged `Job schedule registered` with `{ kind: 'export-cleanup', cron: '0 3 * * *' }`;
     `psql` moves one export's `createdAtUtc` back 8 days; `sendJob('export-cleanup', {})`; after
     `Job finished` that export is gone and a new one stays.
   - Case `a failed job retries with growing waits and then shows as failed` (FAILEDJOBS): `psql`
     adds a trigger on `"Export"` that refuses an update for one fresh admin's account; that admin
     asks for an export; the test waits until `GET /api/v1/jobs/failed` lists it with `attempts` 5
     and `kind` `csv-export`; of the `Job failed` lines for it, the wait between the last two is
     longer than the wait between the first two.
   - Each case has its Python twin in EXPORTJOBSPY or FAILEDJOBS.
   - Test (new repo): `tests/test_jobs_policy.py::test_3_jobs_retry_with_back_off_run_on_schedule_and_run_twice_safely`
     requires the cases from both live runs. Without `LIVE` it checks that both starters' jobs
     core files have the policy numbers.
4. The Jobs screen (FAILEDJOBS for the API, JOBSSCREEN for the screen).
   - API cases in `jobs.e2e-spec.ts` (FAILEDJOBS): `an admin retries a failed job` (after the
     failure above, the trigger is dropped, `POST /api/v1/jobs/:id/retry` gives 202, the export
     becomes `ready`, and the failed list no longer has it); `a member cannot list or retry failed
     jobs` (both `403 ADMIN_ONLY`); `an admin cannot see or retry another organisation's job` (an
     empty list and `404 JOB_NOT_FOUND`).
   - JOBSSCREEN: route `/jobs` in the protected layout, and sidebar and Ctrl+K items for admins
     only, as the change history screen has them. A member who opens `/jobs` sees the text that
     the design names (the API answers 403). The table and texts come from
     `docs/design/FORGE-JOBS-1/SCREENS.md`. Playwright flow `apps/web/e2e/jobs.spec.ts`: `an admin
     retries a failed job on the Jobs screen` (the job fails through the same `psql` trigger; the
     admin clicks Retry; the row goes; axe finds no serious problem).
   - Test (new repo): `tests/test_jobs_screen.py::test_4_admins_see_failed_jobs_and_retry_them`
     requires the API cases and the flow from both live runs.
5. Liveness and readiness (QUEUE, QUEUEPY).
   - TypeScript: `HealthController` gets `live()` and `ready()`; `ready()` calls
     `HealthService.ready()`, which runs ``prisma.$queryRaw`SELECT 1` `` under a 2-second limit.
     The worker's `node:http` server uses the same `HealthService`. `main.ts` adds the two paths
     to the `setGlobalPrefix` exclude list. Python: `app/core/health.py` holds a router with the
     two routes, included by `main.py` and `worker.py`; ready runs `SELECT 1` with a 2-second
     connect and statement limit.
   - `scripts/test.mjs` in both starters, after the browser suite and the `/health` check: `docker
     compose pause database`; `/health/ready` on the API and the worker gives 503 with
     `NOT_READY`, and `/health/live` on both gives 200; `docker compose unpause database`; ready
     gives 200 again within 10 seconds. It prints `Readiness fails while the database is down` and
     `Readiness returns when the database is back`. It runs last, so no other case sees the
     paused database.
   - Test (new repo): `tests/test_jobs_health.py::test_5_api_and_worker_answer_liveness_and_readiness`,
     parameters `react` and `python`: init copies the health files and the compose healthcheck on
     `/health/ready`; under `LIVE` the live run output has both lines.
6. The rules, the guide and existing apps (GUIDE).
   - The database skill (`src/forge/templates/skills/database/SKILL.md`, from
     FORGE-DATABASE-1/SKILL): section 7, "Job tables", becomes "Background jobs" with five rules:
     add a job in the same transaction as its record (`send(..., tx)` with `fromPrisma(tx)`, or
     `defer(db, ...)` before the commit); put the record id in the job data and make a second run
     change nothing; give each kind a time limit and retries with back-off; read in one short
     transaction, do the slow work (mail, files, other services) outside a transaction, and write
     the result in one short transaction; run schedules with pg-boss `schedule` or Procrastinate
     `periodic`, in UTC. Then: no Redis or queue server; pg_cron only for scheduled SQL; in an app
     without the jobs core, the same rules hold with a jobs table read with `SELECT ... FOR UPDATE
     SKIP LOCKED`.
   - `conventions/backend.md`: the layout gets `apps/api/src/worker.ts`, `libs/core/src/jobs/` and
     `libs/jobs/src/`; a "Background jobs" section names `JobsService.send` and `handle`, the job
     kinds, the policy and the worker log lines, and the call-or-event section's last line points
     to it. `conventions/python.md` gets the same section for `app.core.jobs` and `app/worker.py`.
     `conventions/stack.md`: a table row `Background jobs | pg-boss on Postgres (Procrastinate in
     the Python starter) | No queue server; a job commits with its data`; the line "A job queue
     (for example BullMQ) ..." under Added later goes; the keep line `An app set up before this
     release keeps its own background work; to add the worker, follow the steps in backend.md or
     python.md.` `conventions/deploy.md`: the worker is a second service from the same image, with
     the worker command, no public port and a health check on `/health/ready`, and the API's
     `/health/live` and `/health/ready`. The steps to add the worker to an existing app (in
     backend.md and python.md): add the dependency, the jobs core, the worker entry, the compose
     service and the deploy service, then move one piece of request work at a time.
   - `brief.md`, after the database paragraph: `Work that must outlive a request, such as an
     email, a file or a call to another service, runs as a job: add it in the same transaction as
     its record, key it by the record id, and give it a time limit. In an app without a worker,
     follow the steps in backend.md or python.md before you add a job.` `skill.md`'s built-in
     constitution lines get `- Built in: background jobs run in a worker on the app's Postgres;
     no Redis.` Both starters' `README.md` "How it works" names the worker and the Jobs screen.
   - Test: `tests/test_jobs_guide.py::test_6_rules_and_guide_ship_and_existing_apps_keep_their_code`,
     with `adoption` in ("new init", "previous release upgrade and sync"), set up as
     FORGE-DATABASE-1's `test_1`. For `.claude` and `.codex`: the synced database skill has the
     "Background jobs" section with its five rules; `forge work` gives a brief with the paragraph,
     and its conventions folder has the backend and Python sections and the keep line. Adopted
     case only: before the upgrade the fixture commits a `compose.test.yml` with no worker and a
     `package.json` with no pg-boss; after upgrade and sync both are byte for byte the same, and no
     `libs/core/src/jobs` or `apps/api/src/worker.ts` exists.

### New and existing repos

- **New repos** (`forge init --starter`, and `--starter python` with the same HTTP contract): the
  jobs core, the worker and its compose service, invites and exports as jobs, the export button,
  the Jobs screen and the health checks. The skill rules, the brief paragraph, the convention
  pages and the README arrive with setup. Plain `forge init` gets the text and no starter.
- **Existing repos** (on upgrade to this release, after `forge sync`): no app file, compose file,
  dependency, schema or migration changes. The skill rules, the brief paragraph and the convention
  pages arrive with sync, with the steps to add the worker. Tested on the adopted fixture (item 6).
  The starter rules (items 1 to 5) reach only new apps; `tests/test_starter_app.py::test_3`
  (adopted case) already shows that upgrade and sync write no starter file.

## Tasks

<!-- One row per task. Covers: the Done-when numbers it delivers, at most three. Scope: the paths
it may change. Tests: the tests it adds or changes. After: the tasks it waits for. When two tasks
share a function, field, file format or command, the first task pins it: it commits the shared
names and stubs plus one test that crosses both sides, and the tasks that use it list it under
After. Split tasks so each owns its files; shared lines (command table, guide list, registry) go
to one task or a small last wiring task; After only when a task needs another task's code. The
Developer column is optional: the lead fills or changes a GitHub username here, below For the
builders, without another approval. Leave it blank for an unassigned part. Forge next uses
the caller's GitHub login; another developer may start it with a warning. Existing tables
without Developer still work. The moving-parts line stays last: "none", or each new dependency, service, datastore,
queue, background job or abstraction layer, with the Done-when item that needs it. -->

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| QUEUE | Job queue and worker in the TypeScript starter | pg-boss in core with the three kinds and their policy, the worker entry and its compose service, the worker log lines, liveness and readiness on the API and the worker, and the shared test helpers. | 1, 3, 5 | `starter/libs/core/src/jobs/**` (new), `starter/libs/core/src/index.ts`, `starter/libs/core/src/common/json-logger.ts`, `starter/apps/api/src/worker.ts` (new), `starter/apps/api/src/worker.module.ts` (new), `starter/apps/api/src/app.module.ts`, `starter/apps/api/src/main.ts`, `starter/apps/api/src/health/**`, `starter/package.json`, `starter/pnpm-lock.yaml`, `starter/compose.test.yml`, `starter/scripts/test.mjs`, `starter/apps/api/test/helpers.ts`, `starter/apps/api/test/jobs.e2e-spec.ts` (new, the time-limit case), `starter/apps/web/e2e/helpers.ts` (`logEvents` service type only) | `tests/test_jobs_health.py` (`test_5`, `react`, new); `tests/test_jobs_policy.py` (`test_3` policy check, new); the TypeScript time-limit case | FORGE-DATABASE-1/PG18 | no | |
| QUEUEPY | Job queue and worker in the Python starter | Procrastinate in core with the same kinds and policy, revision `0009_jobs`, the Alembic filter, the worker entry and its compose service, the worker log lines, and liveness and readiness on the API and the worker. | 3, 5 | `starter-python/apps/api/app/core/jobs.py` (new), `starter-python/apps/api/app/core/health.py` (new), `starter-python/apps/api/app/core/__init__.py`, `starter-python/apps/api/app/worker.py` (new), `starter-python/apps/api/app/main.py`, `starter-python/apps/api/migrations/env.py`, `starter-python/apps/api/migrations/versions/0009_jobs.py` (new), `starter-python/apps/api/pyproject.toml`, `starter-python/apps/api/uv.lock`, `starter-python/compose.test.yml`, `starter-python/scripts/test.mjs`, `starter-python/apps/api/tests/conftest.py`, `starter-python/apps/api/tests/test_jobs.py` (new, the time-limit case) | `tests/test_jobs_health.py` (`python`); the Python time-limit case | QUEUE, FORGE-DATABASE-1/COLUMNSPY | no | |
| INVITEJOBS | Invite emails as jobs in both APIs | The invite and its job in one transaction, the `invite-email` handler in both APIs, the rollback case, and the test helpers that read the invite link from the worker. | 1, 2 | `starter/libs/organisations/src/organisations.service.ts`, `starter/libs/organisations/src/organisations.module.ts`, `starter/libs/organisations/src/invite-email.handler.ts` (new), `starter/apps/api/test/helpers.ts`, `starter/apps/api/test/jobs.e2e-spec.ts`, `starter/apps/web/e2e/helpers.ts`, `starter/apps/web/e2e/join.spec.ts`, `starter/apps/web/e2e/members.spec.ts`, `starter/apps/web/e2e/history.spec.ts`, `starter-python/apps/api/app/organisations/service.py`, `starter-python/apps/api/app/organisations/tasks.py` (new), `starter-python/apps/api/app/core/mail.py`, `starter-python/apps/api/tests/conftest.py`, `starter-python/apps/api/tests/test_jobs.py`, `starter-python/apps/api/tests/test_invites.py` (helper call only) | `tests/test_jobs_worker.py` (`test_1` invite names and `test_2`, new); the invite and rollback cases in both APIs | QUEUE, QUEUEPY | no | |
| EXPORTJOBS | CSV exports as jobs in the TypeScript API | The jobs module with the Export table, the export request, status and download routes, the `csv-export` handler and the three builders, and the nightly clean-up schedule. | 1, 3 | `starter/libs/jobs/**` (new), `starter/apps/api/prisma/schema/jobs.prisma` (new), `starter/apps/api/prisma/migrations/<after FORGE-DATABASE-1's>_exports/` (new), `starter/libs/core/src/common/csv.ts`, `starter/libs/core/src/index.ts`, `starter/libs/projects/src/**`, `starter/libs/organisations/src/organisations.controller.ts`, `starter/libs/organisations/src/organisations.module.ts`, `starter/libs/history/src/**`, `starter/apps/api/src/app.module.ts`, `starter/apps/api/src/worker.module.ts`, `starter/apps/api/package.json`, `starter/apps/api/tsconfig.json`, `starter/pnpm-lock.yaml`, `starter/scripts/test-build.mjs`, `starter/apps/api/test/jobs.e2e-spec.ts`, `tests/test_starter_tree.py` (libs list, schema set) | `tests/test_jobs_worker.py` (`test_1` export names); `tests/test_jobs_policy.py` (`test_3` case names); the export, second-run and clean-up cases | INVITEJOBS, FORGE-DATABASE-1/COLUMNS | no | |
| EXPORTJOBSPY | CSV exports as jobs in the Python API | The same HTTP contract as EXPORTJOBS in the Python starter: `app.jobs` with the export table, the routes, the `csv-export` task and builders, and the nightly periodic clean-up. | 1, 3 | `starter-python/apps/api/app/jobs/**` (new), `starter-python/apps/api/app/core/csv.py`, `starter-python/apps/api/app/core/__init__.py`, `starter-python/apps/api/app/projects/**`, `starter-python/apps/api/app/organisations/routes.py`, `starter-python/apps/api/app/organisations/tasks.py`, `starter-python/apps/api/app/history/**`, `starter-python/apps/api/app/main.py`, `starter-python/apps/api/migrations/env.py` (model import only), `starter-python/apps/api/migrations/versions/0010_exports.py` (new), `starter-python/apps/api/pyproject.toml` (`jobs internals` contract), `starter-python/apps/api/tests/test_jobs.py`, `starter-python/libs/shared/openapi.json` and `starter-python/libs/shared/src/api-types.ts` (regenerated), `tests/test_python_starter.py` (module and contract lists) | the Python export, second-run and clean-up cases, required by `test_1` and `test_3` | EXPORTJOBS | no | |
| FAILEDJOBS | Failed jobs list and retry in both APIs | The admin-only failed jobs list and retry in both APIs, scoped to the organisation, with the retry and back-off cases. | 3, 4 | `starter/libs/jobs/src/jobs.controller.ts` (new), `starter/libs/jobs/src/jobs.module.ts`, `starter/libs/core/src/jobs/jobs.service.ts`, `starter/libs/shared/src/index.ts`, `starter/apps/api/test/jobs.e2e-spec.ts`, `starter-python/apps/api/app/jobs/routes.py`, `starter-python/apps/api/app/jobs/schema.py`, `starter-python/apps/api/app/core/jobs.py`, `starter-python/apps/api/tests/test_jobs.py`, `starter-python/libs/shared/src/index.ts`, `starter-python/libs/shared/openapi.json` and `starter-python/libs/shared/src/api-types.ts` (regenerated) | `tests/test_jobs_screen.py` (`test_4` API names, new); `tests/test_jobs_policy.py` (the retry case name); the item 3 retry case and the item 4 API cases in both APIs | EXPORTJOBS, EXPORTJOBSPY | no | |
| EXPORTWEB | Export button waits for the file | The shared Export CSV button that asks for the file, shows that it is in preparation and downloads it, on the three list screens, and the old download routes removed from both APIs. | 1 | `starter/apps/web/src/components/export-csv-button.tsx` (new), `starter/apps/web/src/features/projects/pages/projects-page.tsx`, `starter/apps/web/src/features/members/pages/members-page.tsx`, `starter/apps/web/src/features/history/pages/history-page.tsx`, `starter/apps/web/e2e/formats.spec.ts`, `starter/apps/web/e2e/history.spec.ts`, `starter/apps/api/test/exports.e2e-spec.ts`, `starter/libs/projects/src/projects.controller.ts`, `starter/libs/organisations/src/organisations.controller.ts`, `starter/libs/history/src/history.controller.ts`, `starter-python/apps/api/app/projects/routes.py`, `starter-python/apps/api/app/organisations/routes.py`, `starter-python/apps/api/app/history/routes.py`, `starter-python/apps/api/tests/test_*.py` (old export cases), `starter-python/libs/shared/openapi.json` and `starter-python/libs/shared/src/api-types.ts` (regenerated), `tests/test_defaults_formats.py` (`test_4` check and `CSV_API_CASES`) | `tests/test_jobs_worker.py` (`test_1` flow name); `tests/test_defaults_formats.py` (`test_4`); the download flow in both live runs | FAILEDJOBS | yes | |
| JOBSSCREEN | Jobs screen | The admin-only Jobs screen with Retry, and its sidebar and Ctrl+K items for admins, as `SCREENS.md` shows it. | 4 | `starter/apps/web/src/features/jobs/**` (new), `starter/apps/web/src/app.tsx`, `starter/apps/web/src/components/app-shell.tsx`, `starter/apps/web/e2e/jobs.spec.ts` (new), `starter-python/libs/shared/src/index.ts` (only a shared name the screen imports that FAILEDJOBS did not copy), `tests/test_jobs_screen.py` (flow name only) | the flow `an admin retries a failed job on the Jobs screen`, required by `test_4` from both live runs | EXPORTWEB | yes | |
| GUIDE | Job rules and the guide to add a worker | The job rules in the database skill, the worker brief paragraph, the built-in line, the convention pages with the steps to add the worker, and the READMEs, on new and existing repos. | 6 | `src/forge/templates/skills/database/SKILL.md` and its synced copies, `src/forge/templates/brief.md`, `src/forge/templates/skill.md`, `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md` (rewritten by `forge sync`), `src/forge/templates/conventions/backend.md`, `src/forge/templates/conventions/python.md`, `src/forge/templates/conventions/stack.md`, `src/forge/templates/conventions/deploy.md`, `starter/README.md`, `starter-python/README.md` | `tests/test_jobs_guide.py` (`test_6`, new); `tests/test_built_in_defaults_guide.py` (the built-in lines) | FORGE-DATABASE-1/SKILL | no | |

New moving parts: pg-boss in the TypeScript starter and Procrastinate in the Python starter, each a job queue in the app's own Postgres (items 1 to 4); a worker process from the same code, as a second compose and deploy service (items 1 and 5); the `invite-email`, `csv-export` and `export-cleanup` background jobs (items 1 and 3). No Redis and no other server.

## Notes

- **Sources for same-transaction enqueue and the job options.** pg-boss Prisma adapter and the
  `db` option: https://pgboss.io/api/adapters. Queue retry and time-limit options (`retryLimit`,
  `retryDelay`, `retryBackoff`, `retryDelayMax`, `expireInSeconds`): https://pgboss.io/api/queues.
  `findJobs` and `retry`: https://pgboss.io/api/jobs. `schedule` and `schedule: false`:
  https://pgboss.io/api/scheduling. The handler's `signal` at the time limit:
  https://pgboss.io/api/workers. The `supervise`, `schedule` and `migrate` options:
  https://pgboss.io/api/constructor. Procrastinate's `configure(connection=...)` with a psycopg or
  SQLAlchemy connection:
  https://procrastinate.readthedocs.io/en/stable/howto/production/external_connection.html. The
  sync connector: https://procrastinate.readthedocs.io/en/stable/howto/advanced/sync_defer.html.
  `RetryStrategy`, `periodic`, `list_jobs` and `retry_job_by_id`:
  https://procrastinate.readthedocs.io/en/stable/reference.html. Schema SQL and migrations:
  https://procrastinate.readthedocs.io/en/stable/howto/production/migrations.html. Version:
  https://pypi.org/project/procrastinate/.
- **Order.** QUEUE first, after FORGE-DATABASE-1/PG18 (both change `compose.test.yml`). QUEUEPY
  after QUEUE (the health contract and the log lines) and after FORGE-DATABASE-1/COLUMNSPY (the
  Alembic chain). INVITEJOBS after both: its helper change makes the web flows read the worker's
  log, and the Python live run runs the same web flows, so both APIs move in one part. EXPORTJOBS
  after INVITEJOBS (the shared `jobs.e2e-spec.ts` and helpers) and FORGE-DATABASE-1/COLUMNS (the
  migration order); EXPORTJOBSPY after EXPORTJOBS. FAILEDJOBS after both export parts. EXPORTWEB
  after FAILEDJOBS, because both regenerate the Python shared API types. JOBSSCREEN last, after
  EXPORTWEB and the design. GUIDE starts after FORGE-DATABASE-1/SKILL and shares no file with the
  other parts. All parts ship in one release.
- **Order with FORGE-FEATURE-1.** That story's command copies the projects module. EXPORTJOBS and
  EXPORTWEB change the projects export; whichever merges later brings main in first, and the
  copied module then registers its own export builder.
- **Why EXPORTWEB is separate from the export API parts.** The web button needs both APIs to serve
  the new export routes, because the Python live run runs the same web flows. The API parts keep
  the old download routes until EXPORTWEB switches the button and removes them.
- **Part sizes.** Each part is planned under 400 hand-written lines. EXPORTJOBS has the most files
  because a new module is wired in many places (as FORGE-DEFAULTS-1's module list says); most of
  them change one line. Generated `openapi.json` and `api-types.ts` lines come on top.
- **Owner decisions (25 Oct 2026, settled).** A Postgres job queue in both starters from the first
  day: pg-boss in NestJS, Procrastinate in Python, no Redis or BullMQ; a separate worker process
  from the same code, started by Docker Compose; a job added in the same transaction as its data;
  retries with back-off, cron schedules, jobs safe to run twice keyed by the record id, a time
  limit per job, no long transactions; an admin-only Jobs screen with failed jobs and Retry;
  invite emails and the CSV export on the queue; liveness and readiness on both APIs and the
  worker, with readiness failing when the database is down; the job rules in the database skill;
  existing apps unchanged on upgrade, with a guide to add the worker.
- **Planner choices the owner did not make.** (1) All three CSV exports move, through one shared
  path, because the starter keeps one export code path. (2) The export file is stored in an
  `Export` table, and only the person who asked can download it. (3) The invite link travels in
  the job data, and the worker sends it only while it is the newest link (see Risks). (4) The
  policy numbers: 4 retries, a 30-second base wait (1 second in test), at most 1 hour between
  tries, 60 seconds for an invite and 300 seconds for an export or clean-up. (5) The nightly
  clean-up removes exports after 7 days, and it is also the schedule example. (6) `/health` stays
  as the deploy check; `/health/live` and `/health/ready` are new, with a 2-second database check.
  (7) The Jobs screen shows no error text. (8) The TypeScript worker is a Nest application
  context with a small `node:http` server, so it serves no API routes. (9) The readiness check
  pauses the database at the end of `scripts/test.mjs`, so no other case sees it down.
- **Not in this story.** Object storage for export files; a real mail provider (production still
  refuses an invite until a story adds one); a screen for finished or waiting jobs; a cancel
  button; schedules for each organisation.
- No client repo is named anywhere in this story's code, tests, texts or commits.
