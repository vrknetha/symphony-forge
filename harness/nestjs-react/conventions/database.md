# Database Conventions

Prisma + PostgreSQL rules for the modular monolith. Every migration, schema change, and query goes through these.

## Schema Design

### Naming

| Element | Convention | Example |
|---------|-----------|---------|
| Tables | snake_case, plural | `users`, `invoice_line_items` |
| Columns | snake_case | `created_at`, `billing_address_id` |
| Indexes | `idx_{table}_{columns}` | `idx_orders_user_id` |
| Unique | `uq_{table}_{columns}` | `uq_users_email` |
| Foreign keys | `fk_{table}_{ref_table}` | `fk_orders_users` |

### Primary Keys

UUID only. Never auto-increment integers. Use `cuid2` (default) or `nanoid` for URL-friendly IDs.

```prisma
model User {
  id        String   @id @default(cuid())
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")

  @@map("users")
}
```

### Required Columns

Every table gets these three. No exceptions:

| Column | Type | Default |
|--------|------|---------|
| `id` | String (cuid2) | `@default(cuid())` |
| `created_at` | DateTime | `@default(now())` |
| `updated_at` | DateTime | `@updatedAt` |

### Soft Deletes

Nullable `deleted_at` timestamp. Never a boolean `is_deleted` flag.

```prisma
model Invoice {
  id        String    @id @default(cuid())
  deletedAt DateTime? @map("deleted_at")
  createdAt DateTime  @default(now()) @map("created_at")
  updatedAt DateTime  @updatedAt @map("updated_at")

  @@index([deletedAt])
  @@map("invoices")
}
```

### Indexes

- Every foreign key column gets an index
- Add composite indexes for frequent query patterns
- Partial indexes for soft-delete filtering where supported

```prisma
model Order {
  id     String @id @default(cuid())
  userId String @map("user_id")
  status String
  user   User   @relation(fields: [userId], references: [id])

  @@index([userId])
  @@index([userId, status])
  @@map("orders")
}
```

### Enum Strategy

| Stability | Strategy | Example |
|-----------|----------|---------|
| Stable (rarely changes) | Postgres native enum | `order_status: pending, confirmed, shipped` |
| Volatile (changes often) | String + CHECK constraint | Feature flags, tag categories |

```prisma
enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}
```

For volatile sets, use a `String` column validated at the application layer.

## Migrations

### Naming

Format: `YYYYMMDD_HHMMSS_description`

```
20260315_143000_create_users_table
20260315_143500_add_email_index_to_users
20260316_090000_create_invoices_table
```

### Rules

| Rule | Detail |
|------|--------|
| One concern per migration | Don't mix table creation with data backfill |
| Always reversible | Every migration has both `up` and `down` |
| Schema ≠ data | Data migrations in separate files, prefixed `data_` |
| Squash at 20 | When a domain exceeds 20 migrations, squash into a baseline |

Data migration example:

```
20260316_100000_data_backfill_user_display_names
```

### Squashing

When migration count per domain exceeds 20:

1. Generate a baseline migration from current schema state
2. Archive old migrations in `prisma/archive/{domain}/`
3. Test that fresh `prisma migrate deploy` matches production schema

## Prisma Setup

### Multi-Schema (Modular Monolith)

One schema file per domain module. Merged at generation time.

```
prisma/
├── base.prisma          # datasource + generator config
├── modules/
│   ├── auth.prisma      # User, Session, Role
│   ├── billing.prisma   # Invoice, Payment, Subscription
│   └── inventory.prisma # Product, Warehouse, Stock
└── migrations/
```

`base.prisma` contains the datasource and generator block only:

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider      = "prisma-client-js"
  previewFeatures = ["prismaSchemaFolder"]
}
```

### Client Generation

Generate per worktree. Never share a generated client across worktrees.

```bash
# In worktree boot script
npx prisma generate
npx prisma migrate deploy
```

### Repository Pattern

No raw SQL in services. All database access goes through repository classes.

```typescript
// ✅ Correct — repository handles queries
@Injectable()
export class OrderRepository {
  constructor(private prisma: PrismaService) {}

  async findActiveByUser(userId: string): Promise<Order[]> {
    return this.prisma.order.findMany({
      where: { userId, deletedAt: null },
      orderBy: { createdAt: 'desc' },
    });
  }
}

// ❌ Wrong — service talks to Prisma directly
@Injectable()
export class OrderService {
  constructor(private prisma: PrismaService) {}

  async getOrders(userId: string) {
    return this.prisma.$queryRaw`SELECT * FROM orders WHERE user_id = ${userId}`;
  }
}
```

### Soft Delete Middleware

Global Prisma middleware filters deleted records automatically:

```typescript
prisma.$use(async (params, next) => {
  if (params.action === 'findMany' || params.action === 'findFirst') {
    params.args.where = { ...params.args.where, deletedAt: null };
  }
  if (params.action === 'delete') {
    params.action = 'update';
    params.args.data = { deletedAt: new Date() };
  }
  return next(params);
});
```

### Seed Scripts

Must complete in under 5 seconds. Use factories, not raw inserts.

```typescript
// prisma/seed.ts
import { UserFactory, OrderFactory } from './factories';

async function main() {
  const users = await UserFactory.createMany(5);
  await OrderFactory.createMany(10, { userId: users[0].id });
}
```

## Anti-Patterns

### No JSON Columns for Structured Data

```typescript
// ❌ Don't store structured data as JSON
model User {
  id       String @id @default(cuid())
  address  Json   // loses type safety, can't query efficiently
}

// ✅ Use proper relations
model User {
  id        String   @id @default(cuid())
  addresses Address[]
}

model Address {
  id     String @id @default(cuid())
  userId String @map("user_id")
  street String
  city   String
  user   User   @relation(fields: [userId], references: [id])
}
```

### No Nullable Booleans

```typescript
// ❌ Three states (true, false, null) = bugs
isVerified Boolean?

// ✅ Use enum or default
isVerified Boolean @default(false)

// ✅ Or use an enum for multi-state
verificationStatus VerificationStatus @default(PENDING)
```

### No Business Logic in Triggers

Keep all business logic in the application layer. Database triggers are invisible, untestable, and break the layer model.

### No Cross-Module Joins

Modules own their data. If module A needs data from module B, use events to sync a denormalized copy.

```typescript
// ❌ Billing module joins to auth module's users table
SELECT i.*, u.email FROM invoices i JOIN users u ON i.user_id = u.id;

// ✅ Billing stores its own customer_email, synced via event
@OnEvent('user.updated')
async handleUserUpdate(payload: UserUpdatedEvent) {
  await this.invoiceRepo.updateCustomerEmail(payload.userId, payload.email);
}
```
