import {
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { Reflector } from '@nestjs/core';
import { ACCESS_TOKEN_COOKIE } from '../auth.constants';
import { IS_PUBLIC_KEY } from '../../common/decorators/public.decorator';

interface RequestWithCookies {
  cookies?: Record<string, string>;
  headers: Record<string, string | string[] | undefined>;
}

@Injectable()
export class JwtAuthGuard extends AuthGuard('azure-ad') {
  constructor(private readonly reflector: Reflector) {
    super();
  }

  override canActivate(context: ExecutionContext) {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) {
      return true;
    }
    const request = context.switchToHttp().getRequest<RequestWithCookies>();
    const cookieToken = request.cookies?.[ACCESS_TOKEN_COOKIE];
    if (cookieToken && !request.headers.authorization) {
      request.headers.authorization = `Bearer ${cookieToken}`;
    }
    return super.canActivate(context);
  }

  override handleRequest<TUser>(
    error: Error | null,
    user: TUser | false,
  ): TUser {
    if (error || !user) {
      throw error ?? new UnauthorizedException('Authentication required');
    }
    return user;
  }
}
