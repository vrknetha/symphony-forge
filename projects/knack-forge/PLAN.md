# Symphony-Forge v1: Projects + Documents

## What Is This?

An internal KnackLabs platform where teams organize work into projects, and each project contains collaborative documents — plans, specs, ADRs, meeting notes. Engineers log in with Azure AD, create projects, add documents, and collaborate in real-time using a markdown editor powered by Proof SDK.

## Who Uses It?

- **KnackLabs engineers** — log in via Azure AD, create projects, write/edit docs
- **Ravi (admin)** — creates projects, manages team access
- **Agents (later)** — will read/edit docs via API. Not in v1 scope, but the API must support it.

## What We're Building

### Project
- A container for related documents (client engagement, product, internal initiative)
- Has: name, description, slug, status (active/archived), owner, team members
- Team members synced from Azure AD groups OR manually added

### Document (within a project)
- A collaborative markdown document powered by Proof SDK
- Has: title, slug, project_id, doc_type, created_by, proof_doc_slug
- Doc types: `plan`, `spec`, `adr`, `notes`, `retrospective` (extensible enum)
- Each document maps 1:1 to a Proof SDK document (we store the slug + tokens)

### Auth
- Azure AD / Entra ID OIDC login
- Roles: admin (full access), member (project-scoped access)
- Agent API keys (create now, agents use later)

## Key Flows

### Flow 1: Engineer Logs In
1. Engineer visits forge.knacklabs.ai (or localhost:3000)
2. Redirected to Azure AD login
3. After auth → lands on project list (their projects)

### Flow 2: Create Project
1. Click "New Project"
2. Fill: name, description
3. Slug auto-generated from name
4. Creator becomes owner
5. Add team members (search by name/email from Azure AD)

### Flow 3: Add Document to Project
1. Inside project view, click "New Document"
2. Pick type (plan, spec, adr, notes, retro)
3. Enter title
4. System creates Proof SDK document (POST /documents) with appropriate template
5. Redirects to editor — Proof SDK collaborative editor embedded in the page
6. Document auto-saves via Proof SDK's Yjs/Hocuspocus collab

### Flow 4: Edit Document
1. Open project → click document
2. Proof SDK editor loads with the document content
3. Multiple team members can edit simultaneously (Yjs CRDT)
4. Comments and suggestions via Proof SDK's built-in features

### Flow 5: Browse Documents
1. Project view shows document list: title, type, last updated, author
2. Filter by type
3. Search across documents (title + content)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│  ┌───────────────────────────────────────────────┐  │
│  │  React + Vite + Tailwind                      │  │
│  │  ├── Login (Azure AD redirect)                │  │
│  │  ├── Project List                             │  │
│  │  ├── Project Detail (doc list)                │  │
│  │  └── Document Editor (Proof SDK embed)        │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│  API Gateway (Express)                              │
│  ├── /auth/*        → Azure AD OIDC handlers        │
│  ├── /api/*         → NestJS (projects, docs meta)   │
│  └── /documents/*   → Proof SDK (editor, collab)     │
│                                                      │
│  Auth middleware on ALL routes:                       │
│  - /auth/* → public (login/callback/logout)          │
│  - /api/* → JWT from Azure AD required               │
│  - /documents/* → JWT OR API key (for agents later)  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│  Data Layer                                          │
│  ├── PostgreSQL (projects, docs metadata, users)     │
│  └── Proof SDK SQLite (document content, collab)     │
└──────────────────────────────────────────────────────┘
```

## Data Model

```prisma
model User {
  id        String   @id @default(uuid())
  azureOid  String   @unique    // Azure AD object ID
  email     String   @unique
  name      String
  role      Role     @default(MEMBER)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  ownedProjects   Project[]         @relation("ProjectOwner")
  memberships     ProjectMember[]
  createdDocs     Document[]
}

model Project {
  id          String        @id @default(uuid())
  name        String
  slug        String        @unique
  description String?
  status      ProjectStatus @default(ACTIVE)
  ownerId     String
  owner       User          @relation("ProjectOwner", fields: [ownerId], references: [id])
  createdAt   DateTime      @default(now())
  updatedAt   DateTime      @updatedAt

  members     ProjectMember[]
  documents   Document[]
}

model ProjectMember {
  id        String      @id @default(uuid())
  projectId String
  userId    String
  role      MemberRole  @default(EDITOR)
  project   Project     @relation(fields: [projectId], references: [id])
  user      User        @relation(fields: [userId], references: [id])
  createdAt DateTime    @default(now())

  @@unique([projectId, userId])
}

model Document {
  id            String       @id @default(uuid())
  title         String
  slug          String
  docType       DocType      @default(NOTES)
  projectId     String
  project       Project      @relation(fields: [projectId], references: [id])
  createdById   String
  createdBy     User         @relation(fields: [createdById], references: [id])

  // Proof SDK link
  proofDocSlug  String       @unique   // slug from Proof SDK POST /documents
  proofOwnerSecret String              // encrypted, for agent operations later
  proofAccessToken String              // for team member access

  createdAt     DateTime     @default(now())
  updatedAt     DateTime     @updatedAt

  @@unique([projectId, slug])
}

model AgentKey {
  id          String   @id @default(uuid())
  name        String                       // e.g., "codex-worker"
  keyHash     String   @unique             // bcrypt hash of API key
  keyPrefix   String                       // first 8 chars for identification
  capabilities String[]                    // ["read", "comment", "edit"]
  createdAt   DateTime @default(now())
  lastUsedAt  DateTime?
  active      Boolean  @default(true)
}

enum Role {
  ADMIN
  MEMBER
}

enum ProjectStatus {
  ACTIVE
  ARCHIVED
}

enum MemberRole {
  OWNER
  EDITOR
  VIEWER
}

enum DocType {
  PLAN
  SPEC
  ADR
  NOTES
  RETROSPECTIVE
}
```

## Document Templates

When creating a new document, pre-fill based on type:

### Plan
```markdown
# [Title]

## What Are We Building?


## Who Is It For?


## Success Looks Like


## Key Flows


## Data Model (Sketch)


## Open Questions

```

### Spec
```markdown
# [Title]

## Overview


## Requirements

### Functional


### Non-Functional


## API Contract


## Data Model


## Dependencies

```

### ADR (Architecture Decision Record)
```markdown
# ADR: [Title]

## Status
Proposed | Accepted | Deprecated | Superseded

## Context


## Decision


## Consequences

```

### Retrospective
```markdown
# Retro: [Title]

## What Went Well


## What Didn't


## Action Items

```

## API Endpoints

### Auth
- `GET /auth/login` — redirect to Azure AD
- `GET /auth/callback` — handle OAuth callback, set session/JWT
- `POST /auth/logout` — clear session
- `GET /auth/me` — current user info

### Projects
- `GET /api/projects` — list user's projects
- `POST /api/projects` — create project
- `GET /api/projects/:slug` — project detail
- `PATCH /api/projects/:slug` — update project
- `DELETE /api/projects/:slug` — archive project (soft delete)

### Project Members
- `GET /api/projects/:slug/members` — list members
- `POST /api/projects/:slug/members` — add member (by email or azure OID)
- `PATCH /api/projects/:slug/members/:id` — change role
- `DELETE /api/projects/:slug/members/:id` — remove member

### Documents
- `GET /api/projects/:slug/documents` — list documents in project
- `POST /api/projects/:slug/documents` — create document (also creates Proof SDK doc)
- `GET /api/projects/:slug/documents/:docSlug` — document metadata + proof link
- `PATCH /api/projects/:slug/documents/:docSlug` — update metadata (title, type)
- `DELETE /api/projects/:slug/documents/:docSlug` — soft delete

### Agent Keys (admin only)
- `GET /api/agent-keys` — list keys
- `POST /api/agent-keys` — create key (returns raw key once)
- `DELETE /api/agent-keys/:id` — revoke key

### Proof SDK (proxied, auth-wrapped)
- `/documents/*` — all Proof SDK routes, wrapped with auth middleware
- Auth middleware injects Proof token from our DB based on user's project membership

## Pages

### /login
- Azure AD login button
- Redirect to /projects after auth

### /projects
- Project cards: name, description, doc count, last active
- "New Project" button
- Search/filter

### /projects/:slug
- Project header: name, description, members
- Document list: title, type badge, last updated, author
- "New Document" button
- Filter by doc type

### /projects/:slug/docs/:docSlug
- Full-width Proof SDK editor
- Header: title, type badge, project breadcrumb
- Sidebar (collapsible): document metadata, version history

### /settings (admin)
- Agent keys management
- User list

## Tech Decisions

1. **Proof SDK as npm dependency** (not git subtree) — cleaner, pull updates via npm
2. **PostgreSQL for our data, SQLite stays for Proof SDK** — don't fight upstream
3. **JWT tokens** from Azure AD, stored in httpOnly cookie — no localStorage
4. **Proof SDK embedded via iframe or direct React mount** — TBD based on Proof SDK's editor package API
5. **pnpm + Turborepo** for monorepo management
6. **Proof tokens encrypted at rest** in PostgreSQL (ownerSecret is sensitive)

## Repo Structure

```
symphony-forge/
├── apps/
│   ├── web/                          # React + Vite + Tailwind
│   │   ├── src/
│   │   │   ├── features/
│   │   │   │   ├── auth/             # Login, callback, auth guard
│   │   │   │   ├── projects/         # List, create, detail
│   │   │   │   ├── documents/        # List, create, editor embed
│   │   │   │   └── settings/         # Admin: agent keys, users
│   │   │   ├── shared/               # Layout, nav, API client
│   │   │   └── main.tsx
│   │   └── package.json
│   │
│   └── api/                          # NestJS backend
│       ├── src/
│       │   ├── auth/                 # Azure AD OIDC, JWT, guards
│       │   ├── projects/             # Project CRUD + members
│       │   ├── documents/            # Doc CRUD + Proof SDK bridge
│       │   ├── agent-keys/           # API key management
│       │   ├── proof-proxy/          # Auth-wrapped proxy to Proof SDK
│       │   └── common/               # Filters, interceptors, pipes
│       ├── prisma/
│       │   ├── schema.prisma
│       │   ├── migrations/
│       │   └── seed.ts
│       └── package.json
│
├── packages/
│   └── shared/                       # Types, DTOs, shared between apps
│       ├── src/
│       │   ├── types/                # Project, Document, User types
│       │   └── constants/            # Enums, doc templates
│       └── package.json
│
├── conventions/                      # Symphony-forge convention files (existing 20)
├── AGENTS.md
├── PLAN_TEMPLATE.md
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

## What v2 Adds (NOT in this scope)
- Experiment lifecycle (planning → approved → building → measuring → complete)
- Agent worker (Claude critique, Codex build, result collector)
- Convention browser in UI
- Convention validation challenges
- Experiment comparison dashboard
