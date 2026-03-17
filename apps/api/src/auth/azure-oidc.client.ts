import axios from 'axios';
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { jwtVerify, createRemoteJWKSet } from 'jose';

interface AzureTokenResponse {
  access_token: string;
  id_token: string;
}

interface AzureUserClaims {
  email: string;
  name: string;
  oid: string;
}

@Injectable()
export class AzureOidcClient {
  constructor(private readonly configService: ConfigService) {}

  buildAuthorizeUrl(): string {
    const tenantId = this.configService.getOrThrow<string>('auth.tenantId', {
      infer: true,
    });
    const baseUrl = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/authorize`;
    const query = new URLSearchParams({
      client_id: this.configService.getOrThrow<string>('auth.clientId', { infer: true }),
      redirect_uri: this.configService.getOrThrow<string>('auth.callbackUrl', {
        infer: true,
      }),
      response_type: 'code',
      scope: this.configService
        .getOrThrow<string[]>('auth.scopes', { infer: true })
        .join(' '),
    });

    return `${baseUrl}?${query.toString()}`;
  }

  async exchangeCode(code: string): Promise<AzureTokenResponse> {
    const tenantId = this.configService.getOrThrow<string>('auth.tenantId', {
      infer: true,
    });
    const url = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
    const payload = new URLSearchParams({
      client_id: this.configService.getOrThrow<string>('auth.clientId', { infer: true }),
      client_secret: this.configService.getOrThrow<string>('auth.clientSecret', {
        infer: true,
      }),
      code,
      grant_type: 'authorization_code',
      redirect_uri: this.configService.getOrThrow<string>('auth.callbackUrl', {
        infer: true,
      }),
    });

    const response = await axios.post<AzureTokenResponse>(url, payload, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    return response.data;
  }

  async verifyIdToken(idToken: string): Promise<AzureUserClaims> {
    const tenantId = this.configService.getOrThrow<string>('auth.tenantId', {
      infer: true,
    });
    const clientId = this.configService.getOrThrow<string>('auth.clientId', {
      infer: true,
    });
    const jwks = createRemoteJWKSet(
      new URL(
        `https://login.microsoftonline.com/${tenantId}/discovery/v2.0/keys`,
      ),
    );
    const result = await jwtVerify(idToken, jwks, {
      audience: clientId,
      issuer: `https://login.microsoftonline.com/${tenantId}/v2.0`,
    });

    return {
      email: String(result.payload.email ?? result.payload.preferred_username ?? ''),
      name: String(result.payload.name ?? 'KnackLabs User'),
      oid: String(result.payload.oid ?? result.payload.sub ?? ''),
    };
  }
}
