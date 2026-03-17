import cookieParser from 'cookie-parser';
import helmet from 'helmet';
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { Logger } from 'nestjs-pino';
import { AppModule } from './app.module';
import { AppExceptionFilter } from './common/filters/app-exception.filter';
import { ResponseInterceptor } from './common/interceptors/response.interceptor';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  const logger = app.get(Logger);

  app.useLogger(logger);
  app.use(cookieParser());
  app.use(
    helmet({
      contentSecurityPolicy: {
        directives: {
          connectSrc: ["'self'", process.env.WEB_BASE_URL ?? 'http://localhost:5173'],
          defaultSrc: ["'self'"],
          fontSrc: ["'self'"],
          frameAncestors: ["'none'"],
          imgSrc: ["'self'", 'data:', 'https:'],
          objectSrc: ["'none'"],
          scriptSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          upgradeInsecureRequests: [],
        },
      },
      frameguard: { action: 'deny' },
      hsts: { includeSubDomains: true, maxAge: 31_536_000, preload: true },
      noSniff: true,
    }),
  );
  app.enableCors({
    credentials: true,
    maxAge: 3_600,
    methods: ['GET', 'POST', 'PATCH', 'DELETE'],
    origin: (process.env.CORS_ORIGINS ?? 'http://localhost:5173').split(','),
  });
  app.useGlobalPipes(
    new ValidationPipe({
      forbidNonWhitelisted: true,
      transform: true,
      whitelist: true,
    }),
  );
  app.useGlobalFilters(app.get(AppExceptionFilter));
  app.useGlobalInterceptors(app.get(ResponseInterceptor));

  const swagger = new DocumentBuilder()
    .setTitle('Symphony Forge API')
    .setDescription('Projects, documents, auth, and agent key APIs.')
    .setVersion('1.0.0')
    .build();

  SwaggerModule.setup('api/docs', app, SwaggerModule.createDocument(app, swagger));
  await app.listen(Number.parseInt(process.env.API_PORT ?? '3000', 10));
}

void bootstrap();
