import { type CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import type { Request } from 'express';
import { AgentKeysService } from '../agent-keys/agent-keys.service';
import { AuthService } from '../auth/auth.service';
import { authErrors } from '../auth/auth.errors';

interface ProofRequest extends Request {
  agentKey?: Awaited<ReturnType<AgentKeysService['authenticate']>>;
  user?: Awaited<ReturnType<AuthService['authenticateToken']>>;
}

@Injectable()
export class ProofProxyGuard implements CanActivate {
  constructor(
    private readonly agentKeysService: AgentKeysService,
    private readonly authService: AuthService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<ProofRequest>();
    const agentKey = request.header('x-agent-key') ?? request.header('x-api-key');

    if (agentKey) {
      request.agentKey = await this.agentKeysService.authenticate(agentKey);
      return true;
    }

    const authorization = request.header('authorization');
    const bearerToken = authorization?.startsWith('Bearer ')
      ? authorization.replace('Bearer ', '').trim()
      : undefined;
    const cookieToken = request.cookies?.symphony_forge_session;
    const jwt = bearerToken ?? cookieToken;

    if (!jwt) {
      throw authErrors.tokenMissing();
    }

    request.user = await this.authService.authenticateToken(jwt);
    return true;
  }
}
