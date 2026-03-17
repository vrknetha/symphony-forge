import { HttpException, type HttpStatus } from '@nestjs/common';

export type AppExceptionCategory =
  | 'AUTH'
  | 'CONFLICT'
  | 'INTERNAL'
  | 'NOT_FOUND'
  | 'VALIDATION';

interface AppExceptionOptions {
  category: AppExceptionCategory;
  code: string;
  description: string;
  retryable?: boolean;
  status: HttpStatus;
}

export class AppException extends HttpException {
  readonly category: AppExceptionCategory;
  readonly code: string;
  readonly description: string;
  readonly retryable: boolean;

  constructor(options: AppExceptionOptions) {
    const retryable = options.retryable ?? false;
    super(
      {
        category: options.category,
        code: options.code,
        description: options.description,
        retryable,
        statusCode: options.status,
      },
      options.status,
    );

    this.category = options.category;
    this.code = options.code;
    this.description = options.description;
    this.retryable = retryable;
  }
}
