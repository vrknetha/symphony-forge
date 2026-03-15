# API Patterns & Conventions

## API Versioning

- **URL prefix:** All endpoints live under `/api/v1/`, `/api/v2/`, etc.
- **Breaking change = new version.** Renaming fields, removing endpoints, changing response shapes → bump major version.
- **Non-breaking changes stay in current version.** Adding optional fields, new endpoints, additive enum values.
- **Deprecation policy:** Set `Sunset` header with removal date. Minimum 3-month warning before removal.
  ```
  Sunset: Sat, 01 Nov 2025 00:00:00 GMT
  Deprecation: true
  ```

## REST Conventions

### Resource Naming
- **Plural nouns, kebab-case:** `/api/v1/invoice-items`, `/api/v1/user-profiles`
- **Nested resources max 2 levels:** `/api/v1/users/:id/invoices` ✅ — `/api/v1/users/:id/invoices/:id/line-items` ❌
- For deeper access, promote to top-level: `/api/v1/line-items?invoice_id=123`

### HTTP Verbs
| Verb | Usage | Example |
|------|-------|---------|
| `GET` | List or detail | `GET /api/v1/users`, `GET /api/v1/users/:id` |
| `POST` | Create | `POST /api/v1/users` |
| `PATCH` | Partial update | `PATCH /api/v1/users/:id` |
| `DELETE` | Soft delete | `DELETE /api/v1/users/:id` |

**PUT is avoided.** Full-replace semantics are rarely needed and error-prone.

## Response Format

### Success — Single Resource
```json
{ "data": { "id": "u_123", "name": "Alice", "email": "alice@example.com" } }
```

### Success — List
```json
{
  "data": [{ "id": "u_123", "name": "Alice" }],
  "meta": { "total": 42, "page": 1, "pageSize": 20, "hasNextPage": true }
}
```

### Error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": { "email": ["must be a valid email"], "name": ["is required"] }
  }
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| `200` | OK — successful GET/PATCH |
| `201` | Created — successful POST |
| `204` | No Content — successful DELETE |
| `400` | Validation error |
| `401` | Unauthenticated |
| `403` | Forbidden |
| `404` | Not found |
| `409` | Conflict (duplicate, state conflict) |
| `422` | Unprocessable entity |
| `429` | Rate limited |
| `500` | Server error |

## Response Interceptor

```typescript
// src/common/interceptors/response.interceptor.ts
import { CallHandler, ExecutionContext, Injectable, NestInterceptor } from '@nestjs/common';
import { map, Observable } from 'rxjs';

@Injectable()
export class ResponseInterceptor<T> implements NestInterceptor<T> {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      map((result) => {
        if (result?.data && result?.meta) return result; // already formatted (paginated)
        return { data: result };
      }),
    );
  }
}
```

## Pagination

- **Cursor-based preferred** for feeds, real-time data, and any list where rows shift frequently.
- **Offset-based acceptable** for admin dashboards, reports, and stable datasets.
- **Default page size:** 20. **Max:** 100. Values outside range are clamped.

```typescript
// src/common/dto/pagination.dto.ts
import { ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsInt, IsOptional, Max, Min } from 'class-validator';

export class PaginationDto {
  @ApiPropertyOptional({ default: 1, minimum: 1 })
  @IsOptional() @Type(() => Number) @IsInt() @Min(1)
  page?: number = 1;

  @ApiPropertyOptional({ default: 20, minimum: 1, maximum: 100 })
  @IsOptional() @Type(() => Number) @IsInt() @Min(1) @Max(100)
  pageSize?: number = 20;
}

export class PaginatedResult<T> {
  data: T[];
  meta: { total: number; page: number; pageSize: number; hasNextPage: boolean };

  static create<T>(data: T[], total: number, page: number, pageSize: number): PaginatedResult<T> {
    return { data, meta: { total, page, pageSize, hasNextPage: page * pageSize < total } };
  }
}
```

## Filtering & Sorting

Query parameter conventions:
```
GET /api/v1/invoices?status=active&sort=-created_at&search=acme
GET /api/v1/invoices?amount_gte=100&amount_lte=500&sort=amount
```

| Pattern | Meaning |
|---------|---------|
| `?status=active` | Exact match filter |
| `?sort=-created_at` | Sort descending (`-` prefix) |
| `?sort=name` | Sort ascending (no prefix) |
| `?search=query` | Full-text search across searchable fields |
| `?amount_gte=100` | Greater than or equal |
| `?amount_lte=500` | Less than or equal |

## Error Handling

```typescript
// src/common/filters/http-exception.filter.ts
import { ArgumentsHost, Catch, ExceptionFilter, HttpException } from '@nestjs/common';
import { Response } from 'express';

@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const res = ctx.getResponse<Response>();
    const status = exception.getStatus();
    const body = exception.getResponse() as any;

    res.status(status).json({
      error: {
        code: body.code ?? `HTTP_${status}`,
        message: body.message ?? exception.message,
        details: body.details ?? undefined,
      },
    });
  }
}
```

## OpenAPI / Swagger

### Generation
- Auto-generated from NestJS decorators — no hand-written spec files.
- **CI validates** that the generated Swagger spec matches actual TypeScript types.
- **Breaking spec changes fail CI** (detected via `openapi-diff` in pipeline).
- **orval** generates a fully typed frontend client from the spec — no manual API layer.

### Decorator Standards

```typescript
// src/modules/users/users.controller.ts
import { ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';

@ApiTags('Users')
@Controller('api/v1/users')
export class UsersController {
  @Get()
  @ApiOperation({ summary: 'List all users with pagination and filtering' })
  @ApiResponse({ status: 200, description: 'Paginated user list', type: UserListResponseDto })
  @ApiResponse({ status: 401, description: 'Unauthenticated' })
  findAll(@Query() query: ListUsersDto) { /* ... */ }

  @Post()
  @ApiOperation({ summary: 'Create a new user' })
  @ApiResponse({ status: 201, description: 'User created', type: UserResponseDto })
  @ApiResponse({ status: 400, description: 'Validation error' })
  @ApiResponse({ status: 409, description: 'Email already exists' })
  create(@Body() dto: CreateUserDto) { /* ... */ }

  @Patch(':id')
  @ApiOperation({ summary: 'Partially update a user' })
  @ApiResponse({ status: 200, description: 'User updated', type: UserResponseDto })
  @ApiResponse({ status: 404, description: 'User not found' })
  update(@Param('id') id: string, @Body() dto: UpdateUserDto) { /* ... */ }
}
```

### DTO Documentation

```typescript
// src/modules/users/dto/create-user.dto.ts
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class CreateUserDto {
  @ApiProperty({ description: 'User email address', example: 'alice@example.com' })
  email: string;

  @ApiProperty({ description: 'Display name', example: 'Alice Zhang', minLength: 2 })
  name: string;

  @ApiPropertyOptional({ description: 'Role assignment', enum: ['admin', 'member'], default: 'member' })
  role?: string;
}
```

## Documentation Requirements

| Rule | Enforced By |
|------|-------------|
| Every endpoint has `@ApiOperation` with summary | PR review + lint |
| Every DTO field has `@ApiProperty` with description | PR review + lint |
| Response types documented with `@ApiResponse` | PR review + lint |
| Each module has a `README.md` with endpoint overview | Convention |

Module README format:
```markdown
# Users Module
## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/users | List users (paginated) |
| POST | /api/v1/users | Create user |
| GET | /api/v1/users/:id | Get user by ID |
| PATCH | /api/v1/users/:id | Update user |
| DELETE | /api/v1/users/:id | Soft-delete user |
```
