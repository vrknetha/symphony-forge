# Task Tracker — PLAN.md

## What

Internal task tracker for small teams. Create projects, add tasks, assign them, track completion. No integrations, no notifications — just clean CRUD with auth. Exists as a validation project for the symphony-forge harness.

## Who

- **Team leads** — create projects, assign tasks, track progress
- **Team members** — view assigned tasks, update status, comment
- **Admins** — manage users, archive projects

## Flows

1. **Sign in** — User authenticates via OIDC, lands on their project list
2. **Create project** — Lead creates a project, adds team members by email
3. **Add task** — Member creates a task in a project with title, description, priority
4. **Work a task** — Member claims a task, updates status as they progress, adds comments
5. **Track progress** — Lead views project tasks filtered by status, assignee, priority

## Domain Concepts

- **Project** — container for related tasks. Has members with roles. Can be archived.
- **Task** — unit of work inside a project. Has status, priority, optional assignee, optional due date.
- **Comment** — text note on a task. Any project member can comment.
- **User** — authenticated person. Global role (admin/member) plus per-project role (owner/editor/viewer).

## Constraints

- Auth: generic OIDC provider (JWT via JWKS)
- Roles: ADMIN and MEMBER globally, OWNER/EDITOR/VIEWER per project
- Pagination: cursor-based
- No frontend in v1 — API only
- Soft deletes on projects and comments

## Out of Scope (v1)

- Real-time updates (WebSockets)
- File attachments
- Email notifications
- Frontend UI
- Audit log
- Due date reminders
