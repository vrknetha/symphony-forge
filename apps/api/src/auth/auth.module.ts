import { Module } from '@nestjs/common';
import { PassportModule } from '@nestjs/passport';
import { AuthController } from './auth.controller';
import { AuthRepository } from './auth.repository';
import { AuthService } from './auth.service';
import { ApiKeyGuard } from './guards/api-key.guard';
import { AzureOidcGuard } from './guards/azure-oidc.guard';
import { JwtAuthGuard } from './guards/jwt-auth.guard';
import { AzureBearerStrategy } from './strategies/azure-bearer.strategy';
import { AzureOidcStrategy } from './strategies/azure-oidc.strategy';

@Module({
  controllers: [AuthController],
  exports: [
    ApiKeyGuard,
    AuthRepository,
    AuthService,
    AzureOidcGuard,
    JwtAuthGuard,
  ],
  imports: [PassportModule.register({ session: false })],
  providers: [
    AuthRepository,
    AuthService,
    ApiKeyGuard,
    AzureBearerStrategy,
    AzureOidcGuard,
    AzureOidcStrategy,
    JwtAuthGuard,
  ],
})
export class AuthModule {}
