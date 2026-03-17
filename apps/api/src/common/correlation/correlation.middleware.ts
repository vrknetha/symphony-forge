import { Injectable, type NestMiddleware } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import type { NextFunction, Request, Response } from 'express';
import { correlationStorage } from './correlation.storage';

const CORRELATION_ID_HEADER = 'x-correlation-id';

@Injectable()
export class CorrelationMiddleware implements NestMiddleware {
  use(request: Request, response: Response, next: NextFunction): void {
    const incomingId = request.header(CORRELATION_ID_HEADER);
    const correlationId = incomingId?.trim() || randomUUID();

    response.setHeader(CORRELATION_ID_HEADER, correlationId);
    correlationStorage.run({ correlationId }, () => next());
  }
}
