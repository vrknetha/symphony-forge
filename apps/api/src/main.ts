import cookieParser from 'cookie-parser';
import helmet from 'helmet';
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { ConfigType } from '@nestjs/config';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { AppExceptionFilter } from './common/filters/app-exception.filter';
import { ResponseInterceptor } from './common/interceptors/response.interceptor';
import { environment } from './config/environment';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const env = app.get<ConfigType<typeof environment>>(environment.KEY);
  app.setGlobalPrefix('api/v1');
  app.use(cookieParser());
  app.use(
    helmet({
      contentSecurityPolicy: {
        directives: {
          connectSrc: ["'self'"],
          defaultSrc: ["'self'"],
          fontSrc: ["'self'"],
          frameAncestors: ["'none'"],
          imgSrc: ["'self'", 'data:', 'https:'],
          objectSrc: ["'none'"],
          scriptSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
        },
      },
      frameguard: { action: 'deny' },
      hsts: { includeSubDomains: true, maxAge: 31536000, preload: true },
      noSniff: true,
    }),
  );
  app.enableCors({
    credentials: true,
    methods: ['GET', 'POST', 'PATCH', 'DELETE'],
    origin: env.allowedOrigins,
  });
  app.useGlobalFilters(new AppExceptionFilter());
  app.useGlobalInterceptors(new ResponseInterceptor());
  app.useGlobalPipes(
    new ValidationPipe({
      forbidNonWhitelisted: true,
      transform: true,
      whitelist: true,
    }),
  );

  const swagger = new DocumentBuilder()
    .setTitle('Symphony-Forge API')
    .setVersion('1.0.0')
    .build();
  SwaggerModule.setup(
    'api/docs',
    app,
    SwaggerModule.createDocument(app, swagger),
  );

  await app.listen(env.apiPort);
}

void bootstrap();
