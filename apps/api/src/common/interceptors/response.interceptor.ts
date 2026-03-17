import {
  CallHandler,
  type ExecutionContext,
  Injectable,
  type NestInterceptor,
} from '@nestjs/common';
import { map, type Observable } from 'rxjs';

interface PaginatedResponse<T> {
  data: T[];
  meta: {
    hasNextPage: boolean;
    page: number;
    pageSize: number;
    total: number;
  };
}

@Injectable()
export class ResponseInterceptor<T> implements NestInterceptor<T, unknown> {
  intercept(
    _context: ExecutionContext,
    next: CallHandler<T>,
  ): Observable<PaginatedResponse<T> | { data: T }> {
    return next.handle().pipe(
      map((result) => {
        if (isPaginatedResponse(result)) {
          return result;
        }

        return { data: result };
      }),
    );
  }
}

function isPaginatedResponse<T>(
  value: T,
): value is T & PaginatedResponse<unknown> {
  return typeof value === 'object' && value !== null && 'data' in value && 'meta' in value;
}
