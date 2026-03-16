import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { Response } from 'express';
import { ErrorCategory } from '../errors/error-category';

interface ErrorBody {
  category?: ErrorCategory;
  code?: string;
  description?: string;
  details?: Record<string, unknown>;
  message?: string;
  retryable?: boolean;
}

function normalize(status: number, body: ErrorBody) {
  return {
    category: body.category ?? 'system',
    code: body.code ?? `HTTP_${status}`,
    description: body.description ?? body.message ?? 'Unexpected error',
    details: body.details,
    message: body.message ?? 'Request failed',
    retryable:
      body.retryable ?? status >= Number(HttpStatus.INTERNAL_SERVER_ERROR),
  };
}

@Catch(HttpException)
export class AppExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<{ path: string }>();
    const status = exception.getStatus();
    const raw = exception.getResponse();
    const body =
      typeof raw === 'string' ? { message: raw } : (raw as ErrorBody);
    response.status(status).json({
      error: normalize(status, body),
      path: request.path,
      timestamp: new Date().toISOString(),
    });
  }
}
