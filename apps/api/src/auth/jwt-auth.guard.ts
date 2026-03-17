import {
  type CanActivate,
  ExecutionContext,
  Injectable,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { Request } from 'express';
import { PUBLIC_ROUTE_KEY } from '../common/decorators/public.decorator';
import { AuthService } from './auth.service';
import { authErrors } from './auth.errors';

interface RequestWithAuth extends Request {
  cookies?: Record<string, string>;
  user?: unknown;
}

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private readonly authService: AuthService,
    private readonly reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const isPublic = this.reflector.getAllAndOverride<boolean>(PUBLIC_ROUTE_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);

    if (isPublic) {
      return true;
    }

    const request = context.switchToHttp().getRequest<RequestWithAuth>();
    const token = extractToken(request);

    if (!token) {
      throw authErrors.tokenMissing();
    }

    request.user = await this.authService.authenticateToken(token);
    return true;
  }
}

function extractToken(request: RequestWithAuth): string | undefined {
  const authorization = request.header('authorization');

  if (authorization?.startsWith('Bearer ')) {
    return authorization.replace('Bearer ', '').trim();
  }

  return request.cookies?.symphony_forge_session;
}
