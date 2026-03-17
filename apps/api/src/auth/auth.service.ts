import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { AuthenticatedUser } from '@symphony/shared';
import { authErrors } from './auth.errors';
import { authConfig } from '../config/auth.config';
import { AuthRepository } from './auth.repository';
import { toAuthenticatedUser } from './auth.mappers';
import { AzureOidcClient } from './azure-oidc.client';

interface AuthCallbackResult {
  redirectUrl: string;
  sessionToken: string;
  user: AuthenticatedUser;
}

@Injectable()
export class AuthService {
  constructor(
    private readonly authRepository: AuthRepository,
    private readonly azureOidcClient: AzureOidcClient,
    private readonly configService: ConfigService,
  ) {}

  async authenticateToken(token: string): Promise<AuthenticatedUser> {
    const claims = await this.azureOidcClient.verifyIdToken(token);
    const user = await this.authRepository.upsertUser({
      azureOid: claims.oid,
      email: claims.email,
      name: claims.name,
    });

    return toAuthenticatedUser(user);
  }

  getLoginUrl(): string {
    return this.azureOidcClient.buildAuthorizeUrl();
  }

  async handleCallback(code?: string): Promise<AuthCallbackResult> {
    if (!code) {
      throw authErrors.callbackCodeMissing();
    }

    const tokenResponse = await this.azureOidcClient.exchangeCode(code);
    const user = await this.authenticateToken(tokenResponse.id_token);

    return {
      redirectUrl: this.configService.getOrThrow<ReturnType<typeof authConfig>>(
        'app.webBaseUrl',
        { infer: true },
      ),
      sessionToken: tokenResponse.id_token,
      user,
    };
  }
}
