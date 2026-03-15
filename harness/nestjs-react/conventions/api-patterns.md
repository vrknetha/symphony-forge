# API Pattern Conventions

## REST

| Operation | Method | Path | Response |
|-----------|--------|------|----------|
| List | GET | `/resources` | 200 + paginated array |
| Get one | GET | `/resources/:id` | 200 + object, 404 |
| Create | POST | `/resources` | 201 + created |
| Update | PATCH | `/resources/:id` | 200 + updated, 404 |
| Delete | DELETE | `/resources/:id` | 204, 404 |

## Pagination (Cursor-Based)

Request: `?limit=20&cursor=<cursor>`
Response: `{ data, pagination: { limit, cursor, hasMore, total } }`

## Validation

All inputs through class-validator DTOs. Global ValidationPipe with whitelist stripping.

## Auth

`@UseGuards(JwtAuthGuard)` + `@ApiBearerAuth()` on protected routes. `@Public()` for open routes.

## Swagger

Every endpoint: `@ApiOperation`, `@ApiParam`, `@ApiResponse`. OpenAPI spec at `/api/docs-json` feeds orval.

## Serialization

Always return typed DTOs. Never expose raw Prisma objects.
