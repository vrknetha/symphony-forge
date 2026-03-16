import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ConfigModule } from '@nestjs/config';
import { ThrottlerModule } from '@nestjs/throttler';
import { AuthModule } from './auth/auth.module';
import { JwtAuthGuard } from './auth/guards/jwt-auth.guard';
import { AgentKeysModule } from './agent-keys/agent-keys.module';
import { RolesGuard } from './common/guards/roles.guard';
import { environment } from './config/environment';
import { DocumentsModule } from './documents/documents.module';
import { HealthController } from './health/health.controller';
import { PrismaModule } from './prisma/prisma.module';
import { ProjectsModule } from './projects/projects.module';

@Module({
  controllers: [HealthController],
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [environment] }),
    ThrottlerModule.forRoot({
      throttlers: [{ limit: 100, name: 'default', ttl: 60000 }],
    }),
    PrismaModule,
    AuthModule,
    ProjectsModule,
    DocumentsModule,
    AgentKeysModule,
  ],
  providers: [
    { provide: APP_GUARD, useClass: JwtAuthGuard },
    { provide: APP_GUARD, useClass: RolesGuard },
  ],
})
export class AppModule {}
