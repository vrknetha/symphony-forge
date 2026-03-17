# Symphony Forge

Production system for building client software using OpenAI Symphony + harness engineering.

## What This Is

Symphony Forge turns client ideas into shipped software using AI agents as the primary developers. It provides:

- **Discovery** — A structured intake process that drives toward a precise, buildable spec
- **Harness** — Architecture conventions and scaffold prompts that agents follow to generate fresh projects (no frozen templates)
- **Symphony** — OpenAI's multi-agent system, configured to run parallel worktrees on Linear issues

## Structure

```
symphony-forge/
├── skill/SKILL.md                    # Discovery engine — invoke for new projects
├── harness/nestjs-react/
│   ├── SCAFFOLD_PROMPT.md            # The prompt — agent reads this, generates fresh project
│   └── conventions/                  # Architecture, API, testing, linter rules
├── docs/                             # Philosophy, validation loop, setup guides
└── projects/                         # Per-client project workspaces (gitignored)
```

## How It Works

### 1. Discovery

Say: "New project: [client name] — [brief description]"

The discovery skill drives structured intake across multiple sessions, challenging assumptions and pushing toward a precise spec.

### 2. Scaffold

When the spec is ready, give an agent the `SCAFFOLD_PROMPT.md` with the project name filled in. The agent generates a fresh monorepo using latest dependency versions. No frozen template — always current.

### 3. Validate

Build a vertical slice (the riskiest flow, end-to-end) before committing to full development. See [docs/validation-loop.md](docs/validation-loop.md).

### 4. Ship

Connect Symphony to Linear. Issues go in, PRs come out. Each agent gets an isolated worktree with its own DB, ports, and environment.

## Why No Template?

Templates rot. One major version bump and you're maintaining the template instead of building products. The scaffold prompt generates everything fresh — latest NestJS, latest React, latest Prisma. The conventions stay stable; the code stays current.

## Stack (NestJS + React Harness)

**Backend:** NestJS · Prisma · PostgreSQL · Redis · OIDC auth (Azure AD / Cognito / Auth0 per project)  
**Frontend:** React · Vite · TanStack Router · TanStack Query · Zustand · shadcn/ui  
**Tooling:** pnpm workspaces · Turborepo · orval · Vitest · GitHub Actions

## Docs

- [Harness Philosophy](docs/harness-philosophy.md) — Why the harness exists
- [Validation Loop](docs/validation-loop.md) — How to confirm a slice is done
- [Symphony Setup](docs/symphony-setup.md) — Connecting to Linear + running agents
- [Getting Started](docs/getting-started.md) — First project walkthrough
