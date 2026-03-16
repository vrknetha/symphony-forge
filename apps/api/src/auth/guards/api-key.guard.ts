import {
  CanActivate,
  ExecutionContext,
  HttpStatus,
  Injectable,
} from '@nestjs/common';
import { AuthService } from '../auth.service';
import { AppException } from '../../common/errors/app-exception';
import { AuthenticatedUser } from '../../common/types/authenticated-user';

interface ApiKeyRequest {
  headers: Record<string, string | string[] | undefined>;
  user?: AuthenticatedUser;
}

@Injectable()
export class ApiKeyGuard implements CanActivate {
  constructor(private readonly authService: AuthService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<ApiKeyRequest>();
    const header = request.headers['x-api-key'];
    const rawKey = Array.isArray(header) ? header[0] : header;
    if (!rawKey) {
      throw new AppException({
        category: 'authorization',
        code: 'AGENT_KEY_MISSING',
        description: 'The x-api-key header is required for this route.',
        message: 'API key required',
        retryable: false,
        status: HttpStatus.UNAUTHORIZED,
      });
    }
    const user = await this.authService.validateApiKey(rawKey);
    if (!user) {
      throw new AppException({
        category: 'authorization',
        code: 'AGENT_KEY_INVALID',
        description: 'The supplied agent API key is invalid or inactive.',
        message: 'Invalid API key',
        retryable: false,
        status: HttpStatus.UNAUTHORIZED,
      });
    }
    request.user = user;
    return true;
  }
}
