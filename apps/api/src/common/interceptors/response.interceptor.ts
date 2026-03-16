import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from '@nestjs/common';
import { Observable, map } from 'rxjs';

interface WrappedResponse<T> {
  data: T;
  meta?: Record<string, unknown>;
}

@Injectable()
export class ResponseInterceptor<T> implements NestInterceptor<
  T,
  WrappedResponse<T>
> {
  intercept(
    _context: ExecutionContext,
    next: CallHandler<T>,
  ): Observable<WrappedResponse<T>> {
    return next.handle().pipe(
      map((result) => {
        if (typeof result === 'object' && result !== null && 'data' in result) {
          return result as WrappedResponse<T>;
        }
        return { data: result };
      }),
    );
  }
}
