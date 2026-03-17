# @symphony/api

NestJS backend for the scaffolded project.

## Setup

```bash
pnpm install
cp .env.test.example .env.test  # for tests
pnpm prisma:generate
pnpm prisma:migrate
pnpm prisma:seed
```

## Development

```bash
pnpm dev        # watch mode
pnpm build      # production build
pnpm start      # run built output
```

## Testing

```bash
pnpm test                # unit tests (100% coverage required)
pnpm test:integration    # integration tests (real DB)
```

## API Docs

OpenAPI spec auto-generated at `/api/docs` when running.
