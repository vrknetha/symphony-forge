import { HttpStatus, Injectable } from '@nestjs/common';
import { Role } from '@prisma/client';
import { createHash } from 'crypto';
import { IProfile, ITokenPayload } from 'passport-azure-ad';
import { AppException } from '../common/errors/app-exception';
import { AuthenticatedUser } from '../common/types/authenticated-user';
import { AuthRepository } from './auth.repository';

export interface OidcUserPayload {
  accessToken: string;
  user: AuthenticatedUser;
}

function resolveEmail(token: ITokenPayload | IProfile): string | undefined {
  if ('preferred_username' in token && token.preferred_username) {
    return token.preferred_username;
  }
  if ('upn' in token && token.upn) {
    return token.upn;
  }
  if (
    'emails' in token &&
    Array.isArray(token.emails) &&
    typeof token.emails[0] === 'string'
  ) {
    return token.emails[0];
  }
  return undefined;
}

function resolveName(token: ITokenPayload | IProfile): string {
  if ('displayName' in token && token.displayName) {
    return token.displayName;
  }
  if ('name' in token && typeof token.name === 'string' && token.name) {
    return token.name;
  }
  return 'KnackLabs User';
}

function resolveRole(token: ITokenPayload): Role {
  return token.roles?.some((role) => role.toLowerCase().includes('admin'))
    ? Role.ADMIN
    : Role.MEMBER;
}

@Injectable()
export class AuthService {
  constructor(private readonly repository: AuthRepository) {}

  async createOidcUser(
    profile: IProfile,
    accessToken: string,
    roles: string[] = [],
  ): Promise<OidcUserPayload> {
    const token: ITokenPayload = {
      name: profile.displayName,
      oid: profile.oid,
      preferred_username: resolveEmail(profile),
      roles,
      upn: profile.upn,
    };
    const user = await this.syncAzureUser(token);
    return { accessToken, user };
  }

  async syncAzureUser(token: ITokenPayload): Promise<AuthenticatedUser> {
    if (!token.oid) {
      throw new AppException({
        category: 'authorization',
        code: 'AZURE_OID_MISSING',
        description: 'Azure AD token did not include the object identifier.',
        message: 'Invalid Azure AD token',
        retryable: false,
        status: HttpStatus.UNAUTHORIZED,
      });
    }
    const email = resolveEmail(token);
    if (!email) {
      throw new AppException({
        category: 'authorization',
        code: 'AZURE_EMAIL_MISSING',
        description: 'Azure AD token did not include a usable email claim.',
        message: 'Invalid Azure AD token',
        retryable: false,
        status: HttpStatus.UNAUTHORIZED,
      });
    }
    const user = await this.repository.upsertUser({
      azureOid: token.oid,
      email,
      name: resolveName(token),
      role: resolveRole(token),
    });
    return {
      authType: 'human',
      azureOid: user.azureOid,
      capabilities: [],
      email: user.email,
      id: user.id,
      name: user.name,
      role: user.role,
    };
  }

  async validateApiKey(rawKey: string): Promise<AuthenticatedUser | null> {
    const keyHash = createHash('sha256').update(rawKey).digest('hex');
    const agentKey = await this.repository.findActiveAgentKeyByHash(keyHash);
    if (!agentKey) {
      return null;
    }
    await this.repository.touchAgentKey(agentKey.id);
    return {
      authType: 'agent',
      azureOid: null,
      capabilities: agentKey.capabilities,
      email: `${agentKey.name}@agents.knacklabs.local`,
      id: agentKey.id,
      name: agentKey.name,
      role: Role.MEMBER,
    };
  }
}
