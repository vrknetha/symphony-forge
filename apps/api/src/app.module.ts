import { MiddlewareConsumer, Module, type NestModule } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { ThrottlerGuard, ThrottlerModule } from '@nestjs/throttler';
import { LoggerModule } from 'nestjs-pino';
import { appConfig } from './config/app.config';
import { authConfig } from './config/auth.config';
import { proofConfig } from './config/proof.config';
import { CorrelationMiddleware } from './common/correlation/correlation.middleware';
import { AppExceptionFilter } from './common/filters/app-exception.filter';
import { ResponseInterceptor } from './common/interceptors/response.interceptor';
import { buildLoggerConfig } from './common/logger/logger.config';
import { EncryptionService } from './common/security/encryption.service';
import { AuthModule } from './auth/auth.module';
import { DocumentsModule } from './documents/documents.module';
import { AgentKeysModule } from './agent-keys/agent-keys.module';
import { PrismaModule } from './prisma/prisma.module';
import { ProjectsModule } from './projects/projects.module';
import { ProofProxyModule } from './proof-proxy/proof-proxy.module';
import { JwtAuthGuard } from './auth/jwt-auth.guard';
import { RolesGuard } from './auth/roles.guard';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [appConfig, authConfig, proofConfig],
    }),
    LoggerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (configService: ConfigService) =>
        buildLoggerConfig(
          configService.getOrThrow<string>('app.serviceName', { infer: true }),
        ),
    }),
    ThrottlerModule.forRoot({
      throttlers: [{ limit: 100, name: 'default', ttl: 60_000 }],
    }),
    PrismaModule,
    AuthModule,
    ProjectsModule,
    DocumentsModule,
    AgentKeysModule,
    ProofProxyModule,
  ],
  providers: [
    EncryptionService,
    AppExceptionFilter,
    ResponseInterceptor,
    { provide: APP_GUARD, useClass: ThrottlerGuard },
    { provide: APP_GUARD, useClass: JwtAuthGuard },
    { provide: APP_GUARD, useClass: RolesGuard },
  ],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(CorrelationMiddleware).forRoutes('*');
  }
}
