import { Inject, Injectable } from '@nestjs/common';
import { ConfigType } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import {
  IOIDCStrategyOptionWithRequest,
  IProfile,
  OIDCStrategy,
} from 'passport-azure-ad';
import { Request } from 'express';
import { environment } from '../../config/environment';
import { AuthService } from '../auth.service';

function metadataUrl(tenantId: string): string {
  return `https://login.microsoftonline.com/${tenantId}/v2.0/.well-known/openid-configuration`;
}

function cookieKey(secret: string, offset: number): string {
  return secret.padEnd(offset + 32, '0').slice(offset, offset + 32);
}

@Injectable()
export class AzureOidcStrategy extends PassportStrategy(
  OIDCStrategy,
  'azure-oidc',
) {
  constructor(
    private readonly authService: AuthService,
    @Inject(environment.KEY)
    env: ConfigType<typeof environment>,
  ) {
    const options: IOIDCStrategyOptionWithRequest = {
      allowHttpForRedirectUrl: true,
      clientID: env.azureClientId,
      clientSecret: env.azureClientSecret,
      cookieEncryptionKeys: [
        {
          iv: cookieKey(env.appEncryptionKey, 0),
          key: cookieKey(env.appEncryptionKey, 8),
        },
      ],
      identityMetadata: metadataUrl(env.azureTenantId),
      loggingLevel: 'warn',
      loggingNoPII: true,
      passReqToCallback: true,
      redirectUrl: env.azureCallbackUrl,
      responseMode: 'query',
      responseType: 'code',
      scope: ['openid', 'profile', 'email'],
      useCookieInsteadOfSession: true,
      validateIssuer: true,
    };
    super(options);
  }

  validate(
    _request: Request,
    _issuer: string,
    _subject: string,
    profile: IProfile,
    _jwtClaims: Record<string, unknown>,
    accessToken: string,
    _refreshToken: string,
    params: Record<string, unknown>,
  ) {
    const roleClaim = params.roles;
    const roles = Array.isArray(roleClaim)
      ? roleClaim.filter((value): value is string => typeof value === 'string')
      : [];
    return this.authService.createOidcUser(profile, accessToken, roles);
  }
}
