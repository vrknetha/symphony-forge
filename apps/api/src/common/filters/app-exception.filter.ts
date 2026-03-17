import {
  ArgumentsHost,
  Catch,
  type ExceptionFilter,
  HttpStatus,
  Injectable,
} from '@nestjs/common';
import { PinoLogger } from 'nestjs-pino';
import type { Response } from 'express';
import { getCorrelationId } from '../correlation/correlation.storage';
import { AppException } from '../errors/app-exception';

@Catch()
@Injectable()
export class AppExceptionFilter implements ExceptionFilter {
  constructor(private readonly logger: PinoLogger) {
    this.logger.setContext(AppExceptionFilter.name);
  }

  catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();

    if (exception instanceof AppException) {
      response.status(exception.getStatus()).json({
        ...exception.getResponse(),
        correlationId: getCorrelationId(),
      });
      return;
    }

    this.logger.error(
      {
        correlationId: getCorrelationId(),
        exception,
      },
      'unhandled.exception',
    );

    response.status(HttpStatus.INTERNAL_SERVER_ERROR).json({
      category: 'INTERNAL',
      code: 'UNEXPECTED_ERROR',
      correlationId: getCorrelationId(),
      description: 'An unexpected error occurred.',
      retryable: false,
      statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
    });
  }
}
