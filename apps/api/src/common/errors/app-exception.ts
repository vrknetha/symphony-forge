import { HttpException, HttpStatus } from '@nestjs/common';
import { ErrorCategory } from './error-category';

export interface AppExceptionOptions {
  category: ErrorCategory;
  code: string;
  description: string;
  details?: Record<string, unknown>;
  message: string;
  retryable: boolean;
  status: HttpStatus;
}

export class AppException extends HttpException {
  constructor(options: AppExceptionOptions) {
    super(
      {
        category: options.category,
        code: options.code,
        description: options.description,
        details: options.details,
        message: options.message,
        retryable: options.retryable,
      },
      options.status,
    );
  }
}
