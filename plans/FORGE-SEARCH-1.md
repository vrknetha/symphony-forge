# One search across the whole app

6 parts · Risks: none one-way · New moving parts: record events in the starters' core, one search table and a search rebuild command

## What changes for you

- A new client app has one search for the whole app. The search box in the top bar, or Ctrl K,
  opens the existing search panel.
- The panel shows the matching pages and actions first. Then it shows the matching records,
  in one group for each module, with the record's name and its status under it. A click on a
  record opens its detail screen.
- Chips at the top of the panel choose All or one module. On a module's own page, the panel
  starts on that module.
- The search starts at two characters, and runs when the person stops typing for a moment
  (150 ms). With All it shows at most five records for each module, and with a module's chip at
  most 20 records of that module. It shows records only from the person's own organisation,
  and only from the modules that the person can view.
- The best matches come first: a name that looks like the typed text, and records whose text
  has the typed words.
- Each create, change, delete and restore of a record updates the search at once. One command
  refills the search from every module, for example after a data import.
- Each new feature that the feature step builds is in the search at once, by its name and its
  other text fields, with its status under the name. Projects are the first example.
- The app has no cache server. The search reads one table through its indexes.
- Existing apps keep their code. On upgrade they get only the guide text.
Design: docs/design/FORGE-SEARCH-1/ (22df188fc174245f0a65842ce7ba5a7afdd110e4)

## Why

Each list in a client app has its own search, and nothing searches the whole app at once. The
Ctrl K panel lists only pages and actions today. A person who looks for one record must first
know its module. On 25 October 2026 the owner chose one search table that a search module
owns, filled by the in-process events that the module rules already allow, one query for each
search with five results for each module (20 with a module's chip), and search for each new feature from the feature
step.

## Done when

1. **In a new app, the top bar search opens the Ctrl K panel with pages and actions first, then results grouped by module with All and per-module chips; on a module's page it starts on that module, and each result shows its title and status and opens its detail screen.**
2. **One search runs one query from two characters, 150 ms after typing stops, and returns at most five results for each module with All and at most 20 with a module chip, only from the person's organisation and the modules they can view, ranked by title likeness plus word match.**
3. **A create, change, delete or restore of a project changes its search result at once, and no module reads another module's tables.**
4. **One rebuild command refills the search from every module through each module's public service.**
5. **Each feature that the feature command builds is in the search by its name and text fields, with its status as the subtitle.**
6. **Both starters' tests pass, and an existing app's code is unchanged after upgrade; it gets the guide text.**

## Risks

<!-- Each one-way step: deleting data, a destructive migration, a new vendor. -->

Risks: none one-way. Each part reverts with its pull request. The new migration adds one table
in the starters only, which a new app copies at set-up; no existing app gets it.

Trade-off: the record and its Change history row share one transaction, but its search row is
a separate write after it. If the search write fails, the record stays and its search row is old or missing until the rebuild command
runs. The failure goes to the logs.

Trade-off: the search matches part of a name (`desig` finds `Design review`), but only whole
words in the other text fields. It does not match other forms of a word (`designs` does not
find `design`).

Trade-off: with All the panel shows at most five records for each module, and with a module's
chip at most 20. To see more, the person opens the module's list.

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

Each new test file starts with `STORY = "FORGE-SEARCH-1"`. Each test runs the forge command or,
for the starter's own behaviour, reads the files that `forge init` writes or requires the case
names from the starter's own run; no test imports forge. One test per Done-when item, named
`test_<n>_...`; a part that adds a side (Python) adds a parameter to the same test. Live tests
carry `@pytest.mark.platform` and `@pytest.mark.timeout(1800)` and use `live_run` and
`_require_cases` from `tests/test_starter_tree.py` and `live_python_starter` from
`tests/test_python_starter.py`, as `tests/test_defaults_soft_delete.py` does. SEARCHTS adds
`tests/test_search_*.py` to both jobs of `starter-smoke.yml` and to its `paths`.

"Adopted starter app" means the fixture that FORGE-FEATURE-1 sets up: the
`tests/fixtures/adopted-v1.2.2/client` repo with the current starter's files copied in and
committed before the upgrade's sync. "Adopted client" means the same fixture with no starter
files.

All paths under `starter/` mean `src/forge/templates/starter/`, and `starter-python/` means
`src/forge/templates/starter-python/`.

No extra guards for unlikely races or security edge cases (owner rule). No cache server and no
cache layer.

**Plan against the merged starter.** This story starts after FORGE-FEATURE-1 and
FORGE-DATABASE-1. Read the merged starter first; where a path or name below differs from the
merged tree, follow the merged tree.

**Design.** PANEL builds the top bar box, the panel, the chips and the four states as
`docs/design/FORGE-SEARCH-1/SCREENS.md` shows them, with the starter's neutral shadcn/ui theme.

### Words this story pins

The part named first owns each name; later parts use it and list that part under After.

- **Record events (SEARCHTS; SEARCHPY for Python).** The call-or-event rule in
  `conventions/backend.md` allows an in-process event when other modules react after an action
  and the action needs no answer. This story's New moving parts names them, as that rule asks.
  - TypeScript, `libs/core/src/common/record.event.ts`, exported from `@app/core`, provided and
    exported by `CommonModule` as `ErrorReporter` is:
    `type RecordSummary = { type: string; organisationId: string; id: string; title: string; subtitle: string | null; text: string }`,
    `type RecordRef = Pick<RecordSummary, 'type' | 'organisationId' | 'id'>`, and the injectable
    `RecordEvents` with `onChanged(handler: (record: RecordSummary) => Promise<void>)`,
    `onDeleted(handler: (record: RecordRef) => Promise<void>)`,
    `changed(record: RecordSummary): Promise<void>`, `deleted(record: RecordRef): Promise<void>`,
    `addSource(type: string, list: () => Promise<RecordSummary[]>)` and
    `sources(): ReadonlyMap<string, () => Promise<RecordSummary[]>>`. No new package: it is a
    plain list of handlers. `changed` and `deleted` await each handler in turn; a handler that
    throws is logged once as a `warn` line `Record event handler failed` with
    `{ type, id }` in its context, and is not thrown on, so the user's write still succeeds.
  - `type` is the module's plural, the same word as its route and its permissions
    (`projects`, `work-orders`).
  - Python, `app/core/records.py`, exported from `app.core`: frozen dataclasses `RecordSummary`
    (`type`, `organisation_id: UUID`, `id: UUID`, `title`, `subtitle: str | None`, `text`) and
    `RecordRef`, and the functions `on_changed(handler)`, `on_deleted(handler)`,
    `record_changed(db, record)`, `record_deleted(db, ref)`, `add_source(type, list)` and
    `sources()`. A handler takes `(db: Session, record)`; `list` takes `(db: Session)` and
    returns `list[RecordSummary]`. A handler error is rolled back on `db` and logged with the
    same line.
  - The sender calls `changed` or `deleted` after its transaction (the record and its Change
    history row, as FORGE-FEATURE-1 writes them) commits. A `ponytail:` comment at `changed`
    (and `record_changed`) says: the search write is not in that transaction; `search:rebuild`
    repairs a missed event.
- **The search table (SEARCHTS; SEARCHPY for Python).** TypeScript model `SearchEntry` in
  `apps/api/prisma/schema/search.prisma`, migration
  `apps/api/prisma/migrations/20261027000000_search/migration.sql`; Python model `SearchEntry`
  with table `search_entry` in `app/search/models.py`, revision
  `migrations/versions/<next>_search.py`, whose down revision is the Alembic head on main at build
  time (after FORGE-DATABASE-1's `0008_columns` and FORGE-FEATURE-1's history subjects revision). Columns (TypeScript
  names; Python in snake case):
  - `organisationId uuid NOT NULL`, `recordType text NOT NULL`, `recordId uuid NOT NULL`,
    primary key `("organisationId", "recordType", "recordId")`; that key is the owner's unique
    rule, so the table has no other id. No foreign key, as `ChangeRecord` has none, so the
    table needs no line in another module's schema.
  - `title text NOT NULL` with `SearchEntry_title_length CHECK (char_length("title") BETWEEN 1 AND 200)`;
    `subtitle text` (null when the module has no status) with
    `SearchEntry_subtitle_length CHECK (char_length("subtitle") <= 200)`;
    `body text NOT NULL DEFAULT ''` (the searchable text) with
    `SearchEntry_body_length CHECK (char_length("body") <= 100000)`;
    `document tsvector GENERATED ALWAYS AS (to_tsvector('simple', "body")) STORED`;
    `updatedAtUtc timestamptz NOT NULL DEFAULT now()` with the
    `SearchEntry_set_updated_at` trigger from FORGE-DATABASE-1's `set_updated_at()`.
  - Indexes: `CREATE INDEX "idx_SearchEntry_title_search" ON "SearchEntry" USING gin ("organisationId", "title" gin_trgm_ops);`
    (btree_gin lets the organisation lead) and
    `CREATE INDEX "idx_SearchEntry_document" ON "SearchEntry" USING gin ("document");`.
  - Prisma: `document Unsupported("tsvector")?` and the nearest `@@index` lines, with the full
    SQL in the migration, as the database skill's Prisma row says; the drift check
    (`prisma migrate diff ... --script` prints an empty migration; `alembic check` passes) runs
    in the part's live run.
  - `'simple'` is the text search configuration: it has no stemming and no language, so it
    works the same for every client's language.
- **The search endpoint (SEARCHTS; SEARCHPY serves the same contract).**
  `GET /api/v1/search?q=<text>[&type=<module>]`, for any signed-in person, through the usual
  envelope. It is not a feature route, so it has no `@RequirePermission`. Shared zod
  `searchQuerySchema = z.object({ q: z.string().trim().min(2).max(200), type: z.string().max(100).optional() }).strict()`
  and `type SearchResult = { type: string; id: string; title: string; subtitle: string | null }`;
  the response data is `SearchResult[]`. A `q` under two characters gets the usual
  `400 VALIDATION_FAILED` of the list queries.
  - The modules the caller may see are the caller's permissions that end in `.view`, with that
    end cut off (`permissionsFor(role)` in TypeScript, `permissions_for(role)` in Python). A
    `type` that is not one of them gives no results.
  - One SQL query (`prisma.$queryRaw`; SQLAlchemy `text()`), with `$limit` 5 without `type`
    and 20 with it (the module chip; the owner settled both limits on 25 October 2026):

    ```sql
    WITH input AS (SELECT websearch_to_tsquery('simple', $q) AS words)
    SELECT "recordType" AS type, "recordId" AS id, title, subtitle FROM (
      SELECT e.*, similarity(e.title, $q) + ts_rank(e.document, input.words) AS score,
             row_number() OVER (PARTITION BY e."recordType"
               ORDER BY similarity(e.title, $q) + ts_rank(e.document, input.words) DESC, e."updatedAtUtc" DESC) AS n
      FROM "SearchEntry" e, input
      WHERE e."organisationId" = $organisationId
        AND e."recordType" = ANY($types)
        AND (e.title ILIKE '%' || $q || '%' OR e.document @@ input.words)
    ) ranked
    WHERE n <= $limit
    ORDER BY score DESC, "updatedAtUtc" DESC;
    ```

    The rank is the trigram likeness of the title (0 to 1) plus the word rank of the text
    (about 0 to 1), added with equal weight. The web groups the results in the order it gets
    them, so the module with the best result comes first.
- **The search module (SEARCHTS; SEARCHPY).** TypeScript library `libs/search`, package
  `@app/search`, wired as `libs/history` is (FORGE-DEFAULTS-1's module wiring list):
  `search.module.ts`, `search.service.ts` (`search(principal, query)`, `upsert(record)`,
  `remove(ref)`, and RECORDSTS's `rebuild()`), `search.controller.ts`, `search.handler.ts`
  (registers `upsert` and `remove` with `RecordEvents` in `onModuleInit`) and `index.ts`.
  `@app/search` uses only `@app/core` and `@app/shared`. Python `app/search/` with
  `__init__.py`, `models.py`, `schema.py`, `service.py` (with the handlers, registered at
  import) and `routes.py`, a `search internals` contract in `apps/api/pyproject.toml`, the
  model import in `migrations/env.py` and the router in `main.py`. `upsert` is
  `INSERT ... ON CONFLICT ("organisationId", "recordType", "recordId") DO UPDATE`; `remove` is
  a plain `DELETE` (the table has no `deletedAtUtc`, so the soft delete trigger is not on it).
- **A module's search file (RECORDSTS; RECORDSPY for Python).** `libs/projects/src/projects.search.ts`
  exports `toProjectRecord(project): RecordSummary`. Python `app/projects/search.py` has
  `to_project_record(project) -> RecordSummary`. The three field lines sit between a new pair of
  marks, `// forge:search` and `// forge:end-search` (`# forge:search` in Python):
  `title` (the first `text` field, the name that FORGE-FEATURE-1 requires every feature to
  have, and its list search), `subtitle` (the first field whose kind has `subtitle = true`, else `null`)
  and `text` (the title field and every other field whose kind has `search_text = true`,
  joined with a space, empty ones left out). For projects: `title: project.name`, `subtitle: project.status`,
  `text: project.name`.
- **The feature service's calls (RECORDSTS; RECORDSPY).** `ProjectsService` calls
  `this.records.changed(toProjectRecord(project))` after create, after a replace and after a
  restore, and `this.records.deleted({ type: 'projects', organisationId, id })` after the soft
  delete, each after the transaction that holds the write and its Change history row. In `onModuleInit` it calls
  `this.records.addSource('projects', () => this.searchRecords())`, where `searchRecords()`
  returns `toProjectRecord` of every project that is not deleted, in every organisation (keyset
  pages through the projects table's own index, not one large read). Python:
  the same calls in `ProjectService`, and `add_source("projects", ...)` at import of
  `app/projects/search.py`. These lines have no field names, so the feature command copies
  them as plain renamed lines.
- **The kind table keys (RECORDSTS).** `src/forge/templates/feature/kinds.toml` gets two
  non-database keys: `search_text` (`true` for `text` and `long-text`) and `subtitle` (`true`
  for `status`). `feature.py` reads them from the table and holds no kind list of its own, as
  FORGE-FEATURE-1 requires.
- **The rebuild (RECORDSTS; RECORDSPY).** `SearchService.rebuild(): Promise<Record<string, number>>`
  deletes every row and inserts every source's records in one transaction, and returns the count
  for each type. A `ponytail:` comment names its ceiling: it holds every record in memory and
  writes them in one transaction; write in batches when the app passes about 100,000 records. Entry
  `apps/api/src/search-rebuild.ts` (`NestFactory.createApplicationContext(AppModule)`, so every
  module's `onModuleInit` registers its source first) and the root `package.json` script
  `"search:rebuild": "node apps/api/dist/search-rebuild.js"`, run as
  `corepack pnpm run search:rebuild`. Python `app/search/rebuild.py`, run from `apps/api` as
  `uv run python -m app.search.rebuild`; it imports `app.main`, so every module registers its
  source first. Both print one line for each type, `Search rebuilt: projects 3`.
- **Web (PANEL).** `apps/web/src/features/search/hooks/search-hooks.ts` with
  `useSearch(text: string, type?: string)`: a small debounce inside the file (150 ms, no
  package), enabled only when the trimmed text has two or more characters, query key
  `['search', text, type]`, and the old results kept until the new ones arrive. The modules
  for the chips and the short-text hint are the signed-in account's `permissions` that end in
  `.view`, in sidebar order. A module's label is its type with hyphens as spaces and the first
  letter in capitals (`work-orders` gives `Work orders`); a result opens `/<type>/<id>`; the
  subtitle shows with its first letter in capitals. The panel starts on the module whose type is
  the first part of the path (`/projects/...`) when the person can view it, else on All.
  `CommandDialog` in `components/ui/command.tsx` passes a `shouldFilter` prop to its `Command`;
  the panel sets it to `false` and filters pages and actions itself with a case-insensitive
  contains, so the existing flow `Ctrl+K opens search and goes to Projects` keeps passing.

### Done-when details

1. The panel (PANEL).
   - `SearchBox` in `components/app-shell.tsx` becomes the top bar box of SCREENS.md, and opens
     the existing `CommandDialog` with the groups, chips and states of SCREENS.md. Pages and
     actions are the items that the app shell already has (FORGE-FEATURE-1 adds one for each
     feature); a module chip hides them and sends `type`.
   - Flows in `apps/web/e2e/search.spec.ts`: `the top bar search finds a project and opens its
     detail screen` (sign up, create a project; type its name in the top bar box; the
     `Pages and actions` group is above the `Projects` group; the result shows the name and
     `Active`; Enter opens `/projects/<id>` with the name as its heading; axe finds no serious
     problem in the open panel), `a module chip shows up to 20 of that module` (with 22 projects
     added through the API, All shows five in the `Projects` group and the `Projects` chip shows
     20) and `search on a module page starts on that module` (on
     `/projects` the `Projects` chip has `aria-pressed="true"` and no pages show; `All` brings
     back the pages; on `/settings` the panel starts on `All`).
   - Test `tests/test_search_panel.py::test_1_the_top_bar_search_opens_one_panel_for_the_whole_app`,
     parameters `typescript` and `python`, live: requires the three flows from the run. The
     existing-repo side is test_6.
2. One query (SEARCHTS and SEARCHPY for the API, PANEL for the web side).
   - API cases in `apps/api/test/search.e2e-spec.ts`, with rows added through the `psql` helper
     so they need no feature code: `search ranks title and word matches and returns five per
     module` (seven `projects` rows of the caller's organisation, one titled `Launch plan`;
     `q=launch plan` returns five rows and `Launch plan` first; a row whose `body` alone has
     the word `budget` comes back for `q=budget`; with `type=projects`, seven rows come back),
     `search returns only the caller's organisation and the modules they can view` (a row of
     another organisation and a row of type `secrets`, which no role can view, never come back;
     `type=secrets` returns none), and `search needs two characters` (`q=a` gets 400). Python
     HTTP cases in `apps/api/tests/test_search.py` with the snake names that FORGE-DEFAULTS-1
     pins.
   - Flow in `search.spec.ts` (PANEL): `search waits for two characters and a pause`: count the
     `GET **/api/v1/search?*` requests; type `p` and wait 300 ms: none; type `roject` with a
     30 ms delay between keys: exactly one request, 150 ms or more after the last key.
   - Test `tests/test_search_query.py::test_2_one_query_returns_five_per_module_for_the_callers_organisation_and_views`,
     parameters `typescript` and `python`. Not live: `forge init --starter` (or
     `--starter python`) writes the migration (or revision) byte for byte, and it holds the
     primary key, the generated `document` column, both index statements and the trigger line.
     Live: requires the API cases (SEARCHTS, SEARCHPY) and the flow (PANEL); the drift check
     prints an empty migration (`alembic check` passes). The existing-repo side is test_6.
3. Kept in step, no cross-module reads (RECORDSTS, RECORDSPY).
   - API case in `apps/api/test/projects.e2e-spec.ts`: `a project's search result follows its
     create, change, delete and restore` (create: `/search?q=<name>` has it with subtitle `active`;
     replace with a new name and `archived`: the new name finds it with `archived`, and the old
     name does not; delete: the name finds nothing; restore as the admin: the name finds it again). The search term is the title field's value,
     read in the case from one line between `// forge:search` marks, so the feature command's
     copy reads its own title field. Python: the same case in `apps/api/tests/test_projects.py`.
   - Not live, in the test: no file under `libs/search/src` (Python `app/search/`) names a model
     or table of another module's schema file, and no file outside them names `SearchEntry` or
     `search_entry`. Nx's boundary lint and the import-linter `search internals` contract hold
     the imports.
   - Test `tests/test_search_records.py::test_3_a_record_change_changes_its_search_result_at_once`,
     parameters `typescript` and `python`: the not-live check, and live, the case from the run.
     The existing-repo side is test_6.
4. Rebuild (RECORDSTS, RECORDSPY).
   - API case in `search.e2e-spec.ts`: `the search rebuild refills every module's records`
     (create a project; `psql` `DELETE FROM "SearchEntry"`; the search finds nothing; run
     `node apps/api/dist/search-rebuild.js` in the `api` service with
     `docker compose -f compose.test.yml exec -T api`; its output has `Search rebuilt: projects`;
     the search finds the project). Python: the same with `uv run python -m app.search.rebuild`
     (or the command the Python `api` image runs Python with).
   - Test `tests/test_search_records.py::test_4_one_command_rebuilds_the_search_from_every_module`,
     parameters `typescript` and `python`, live: requires the case. Not live: the starter's root
     `package.json` has the `search:rebuild` script. The existing-repo side is test_6.
5. The feature command (RECORDSTS for TypeScript, RECORDSPY for Python).
   - `feature.py` renders the `forge:search` marks from the kind table keys above. The rest of
     the copy of `projects.search.ts` and of the service lines is a plain renamed copy.
   - Test `tests/test_search_feature.py::test_5_each_new_feature_is_searchable_by_its_name_and_text`,
     parameters `typescript` and `python`. In a new starter app,
     `forge task feature customers --one customer --field name:text` and
     `forge task feature invoices --one invoice --field title:text --field code:text --field
     notes?:long-text --field contact?:email --field state:status(draft|sent|void)`: the invoices
     search file has the title from `title` only, the subtitle from `state`, and text from
     `title`, `code` and `notes` but not `contact`; the customers file has `subtitle: null` (Python `None`); the service has the
     `changed` (create, replace, restore), `deleted` and `addSource('invoices', ...)` calls. Live (one cached run with the
     FORGE-FEATURE-1 feature tests): the generated case `an invoice's search result follows its
     create, change, delete and restore` passes. Adopted case: in the adopted starter app, the same lines
     write the same search files with the same text.
6. Both starters pass, existing apps unchanged (every part keeps the starters' tests passing;
   GUIDE for the texts).
   - `brief.md`, after FORGE-FEATURE-1's feature paragraph: `In an app that has libs/search
     (Python: app/search), each feature's create, change and delete sends its record event
     (RecordEvents.changed or deleted; Python record_changed or record_deleted) after the write,
     and the feature registers a source of all its records for the rebuild. forge task feature
     writes both. After a data import, or when search misses a record, run the rebuild:
     corepack pnpm run search:rebuild (Python: uv run python -m app.search.rebuild in apps/api).`
   - Convention pages: `backend.md` (the search module in the layout; the record events as the
     example of the call-or-event rule; the rebuild), `python.md` (the same for `app/search` and
     `app.core.records`), `frontend.md` (the top bar search and the panel are the one search; a
     list keeps its own search box for its own filter), `stack.md` (the keep line `An app set up
     before this release keeps its own search.`). The starter's `README.md` "How it works"
     names the search, the record events and the rebuild. `docs/guide.md`: one sentence in
     FORGE-FEATURE-1's paragraph: a new feature is in the app search at once.
   - Test `tests/test_search_guide.py::test_6_existing_apps_keep_their_code_and_get_the_search_rules`,
     with `adoption` in ("new init", "previous release upgrade and sync"), set up as `test_4` of
     `tests/test_app_constitution.py`: `forge work` gives a brief with the paragraph, and its
     conventions folder has the new lines and the keep line. Adopted case only: before the
     upgrade the fixture commits `apps/web/src/components/app-shell.tsx` with its own search
     and an `apps/api/prisma/schema/shop.prisma`; after upgrade and sync both are byte for byte
     the same, and no `libs/search` or `app/search` exists.

### New and existing repos

- **New repos** (`forge init --starter`, and `--starter python` with the same HTTP contract):
  the search module and table, the record events, projects in the search, the rebuild command,
  the top bar search and panel, and the feature command's search file. The brief paragraph and
  the convention pages arrive with set-up. Plain `forge init` gets the texts and no starter;
  `forge task feature` refuses there, as FORGE-FEATURE-1 says.
- **Existing repos** (on upgrade to this release, after `forge sync`): the brief paragraph and
  the convention pages, which name `libs/search` as the condition. No app file, schema or
  migration changes. An app made from the starter before this release has no `libs/search`, so
  a feature copy's `RecordEvents` calls would not compile there. RECORDSTS (RECORDSPY for
  Python) adds `libs/search/src/search.module.ts` (Python `apps/api/app/search/`) to
  FORGE-FEATURE-1's starter check, so such an app gets the refusal that names it. Tested on the
  adopted fixtures (items 5 and 6).

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
| SEARCHTS | Search table and query in the TypeScript API | The record events in core, the search module with its table, indexes, handlers and one ranked query, and the shared search schema. | 2 | `starter/libs/core/src/common/record.event.ts` (new), `starter/libs/core/src/common/common.module.ts`, `starter/libs/core/src/index.ts`, `starter/libs/search/**` (new), `starter/apps/api/prisma/schema/search.prisma` (new), `starter/apps/api/prisma/migrations/20261027000000_search/` (new), `starter/libs/shared/src/index.ts`, `starter/apps/api/src/app.module.ts`, `starter/apps/api/package.json`, `starter/apps/api/tsconfig.json`, `starter/pnpm-lock.yaml`, `starter/scripts/test-build.mjs`, `starter/apps/api/test/search.e2e-spec.ts` (new), `tests/test_starter_tree.py` (libs list, schema set), `.github/workflows/starter-smoke.yml` | `tests/test_search_query.py` (`test_2`, `typescript`, new); the API cases of item 2 | FORGE-DATABASE-1/IDS, FORGE-DATABASE-1/COLUMNS, FORGE-FEATURE-1/ACCESS | no | |
| SEARCHPY | Search table and query in the Python API | The same HTTP contract as SEARCHTS in the Python starter: the record events in core, the search module, its table and indexes, and the query. | 2 | `starter-python/apps/api/app/core/records.py` (new), `starter-python/apps/api/app/core/__init__.py`, `starter-python/apps/api/app/search/**` (new), `starter-python/apps/api/app/main.py`, `starter-python/apps/api/migrations/env.py` (model import only), `starter-python/apps/api/migrations/versions/<next>_search.py` (new), `starter-python/apps/api/pyproject.toml` (`search internals` contract), `starter-python/apps/api/tests/test_search.py` (new), `starter-python/libs/shared/src/index.ts`, `starter-python/libs/shared/openapi.json` and `starter-python/libs/shared/src/api-types.ts` (regenerated), `tests/test_python_starter.py` (module and contract lists) | `tests/test_search_query.py` (`test_2`, `python`); the Python HTTP cases of item 2 | SEARCHTS, FORGE-DATABASE-1/COLUMNSPY, FORGE-FEATURE-1/ACCESS | no | |
| RECORDSTS | Projects and new features in search, TypeScript | The projects search file and its marks, the record event calls and the source in the projects service, the rebuild and its command, the two kind table keys, and the feature command's search rendering and starter check line. | 3, 4, 5 | `starter/libs/projects/src/projects.search.ts` (new), `starter/libs/projects/src/projects.service.ts`, `starter/libs/search/src/search.service.ts` (rebuild only), `starter/apps/api/src/search-rebuild.ts` (new), `starter/package.json` (one script), `starter/apps/api/test/projects.e2e-spec.ts`, `starter/apps/api/test/search.e2e-spec.ts` (rebuild case), `src/forge/feature.py` (search marks and the starter check line), `src/forge/templates/feature/kinds.toml` (two keys) | `tests/test_search_records.py` (`test_3`, `test_4`, `typescript`, new); `tests/test_search_feature.py` (`test_5`, `typescript`, new) | SEARCHTS, FORGE-FEATURE-1/WEB, FORGE-DATABASE-1/KINDS | no | |
| RECORDSPY | Projects and new features in search, Python | The same as RECORDSTS in the Python starter and the feature command's Python copy. | 3, 4, 5 | `starter-python/apps/api/app/projects/search.py` (new), `starter-python/apps/api/app/projects/service.py`, `starter-python/apps/api/app/search/service.py` (rebuild only), `starter-python/apps/api/app/search/rebuild.py` (new), `starter-python/apps/api/tests/test_projects.py`, `starter-python/apps/api/tests/test_search.py` (rebuild case), `src/forge/feature.py` (the Python search marks and starter check line only) | `tests/test_search_records.py` (`test_3`, `test_4`, `python`); `tests/test_search_feature.py` (`test_5`, `python`) | RECORDSTS, SEARCHPY, FORGE-FEATURE-1/PY | no | |
| PANEL | The top bar search and panel | The top bar box, the panel with pages and actions, module groups, chips and the four states, the debounced search hook, and the flows, as SCREENS.md shows them. | 1, 2 | `starter/apps/web/src/components/app-shell.tsx`, `starter/apps/web/src/components/ui/command.tsx` (`shouldFilter` pass-through only), `starter/apps/web/src/features/search/**` (new), `starter/apps/web/e2e/search.spec.ts` (new), `starter-python/libs/shared/src/index.ts` (only a shared name the panel imports that SEARCHPY did not copy) | `tests/test_search_panel.py` (`test_1`, new); `tests/test_search_query.py` (`test_2`, the flow name); the flows pass in both live runs | RECORDSTS, RECORDSPY, FORGE-FEATURE-1/WEB | yes | |
| GUIDE | Brief and convention pages | The brief paragraph, the convention pages, the guide sentence and the starter README, on new and existing repos. | 6 | `src/forge/templates/brief.md`, `src/forge/templates/conventions/backend.md`, `python.md`, `frontend.md`, `stack.md`, `docs/guide.md`, `starter/README.md` | `tests/test_search_guide.py` (`test_6`, new) | FORGE-FEATURE-1/GUIDE, FORGE-DATABASE-1/SKILL | no | |

New moving parts: the record events (`RecordEvents` in TypeScript core, `app.core.records` in Python), a plain in-process list of handlers and sources with no new package, which each feature sends and the search module receives (items 3 and 5); the `SearchEntry` table in both starters (item 2); the search rebuild command (item 4). No cache server.

## Notes

- **Order.** SEARCHTS first; SEARCHPY after it (the HTTP contract and the test file). RECORDSTS
  after SEARCHTS; RECORDSPY after RECORDSTS and SEARCHPY (both edit `feature.py` and add Python
  names to the same tests). PANEL last of the code parts: its flows run against both APIs and
  need projects in the search. GUIDE shares no file with the other parts and starts at once,
  after the two stories' parts that also change the brief and the convention pages. All parts
  ship in one release.
- **Why RECORDSTS holds the feature command's change.** The command copies every projects
  file. A `projects.search.ts` with `project.name` in it would give an invoice copy that does not
  compile, so the search file, its marks and their rendering land in one part.
- **Part sizes.** Each part is planned under 400 hand-written lines. SEARCHTS is the largest at
  about 300, most of it the new module's wiring files, which follow `libs/history`. The Python
  parts also regenerate `openapi.json` and `api-types.ts`; those lines come on top.
- **Owner decisions (25 Oct 2026, settled).** One search module in both starters owns one
  table: organisation, record type, record id, title, subtitle, a stored generated tsvector of
  the searchable text, updated time; a trigram GIN index on the title with the organisation in
  front through btree_gin, a GIN index on the tsvector, unique on organisation, type and id.
  Each feature's create, change and delete sends an in-process event and the search module
  writes or deletes the row; no module reads another module's tables; a rebuild command refills
  the table through each module's public service. One query for each search, from two
  characters, 150 ms after typing stops, at most five results for each type, only the types
  the person can view (`<plural>.view`), ranked by trigram likeness on the title plus `ts_rank`
  on the text. The top bar search opens the existing Ctrl K panel, with pages and actions first,
  then results by module, All and per-module chips, the module's own chip first on its page,
  title and status, and the detail screen on a click. The feature command registers each new
  feature's name and text fields and its status; projects first. No cache server. Existing
  client apps are not changed. Later the same day: a module chip shows up to 20 results and All
  shows five for each module, as the design says; the record and its Change history row share
  one transaction (FORGE-FEATURE-1), and this story's search writes stay separate.
- **Planner choices the owner did not make.** (1) The record events are a plain list of
  handlers in core, not a package, and a handler error is logged, not thrown. (2) The event
  carries the title, subtitle and text, so the search module never reads the feature's table.
  (3) The searchable text is the name field and every other `text` and `long-text` field; an
  `email` field is not in it. (4) The `'simple'` text search configuration, with no stemming. (5) The
  rank adds the two scores with equal weight. (6) The modules a person can view come from their
  `.view` permissions, in the API and in the web. (7) The table's key is its unique
  organisation, type and id, with no other id column. (8) The endpoint takes an optional `type` for
  the module chip. (9) The rebuild empties and refills the whole table in one
  transaction.
- **Not in this story.** A "see all results" link; search in Members or Change history, which
  have no `.view` permission; typo matches beyond trigram likeness; highlights of the matched
  words.
- No client repo is named anywhere in this story's code, tests, texts or commits.
