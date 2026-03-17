import { getCorrelationId } from '../correlation/correlation.storage';
import { sanitizeObject } from './pii-serializer';

export function buildLoggerConfig(service: string) {
  return {
    pinoHttp: {
      customProps: () => ({
        correlationId: getCorrelationId(),
        service,
      }),
      level: process.env.LOG_LEVEL ?? 'info',
      redact: {
        censor: '[REDACTED]',
        paths: ['req.headers.authorization', 'req.headers.cookie'],
      },
      serializers: {
        req: (request: { method?: string; url?: string }) =>
          sanitizeObject({
            method: request.method,
            url: request.url,
          }),
        res: (response: { statusCode?: number }) =>
          sanitizeObject({
            statusCode: response.statusCode,
          }),
      },
      transport:
        process.env.NODE_ENV !== 'production'
          ? {
              options: { colorize: true },
              target: 'pino-pretty',
            }
          : undefined,
    },
  };
}
