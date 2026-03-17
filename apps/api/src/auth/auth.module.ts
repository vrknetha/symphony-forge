import { Module } from '@nestjs/common';
import { AuthController } from './auth.controller';
import { AuthRepository } from './auth.repository';
import { AuthService } from './auth.service';
import { AzureOidcClient } from './azure-oidc.client';

@Module({
  controllers: [AuthController],
  exports: [AuthRepository, AuthService],
  providers: [AuthRepository, AuthService, AzureOidcClient],
})
export class AuthModule {}
