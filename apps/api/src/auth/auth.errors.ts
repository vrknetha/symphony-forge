import { HttpStatus } from '@nestjs/common';
import { AppException } from '../common/errors/app-exception';

export const authErrors = {
  callbackCodeMissing: () =>
    new AppException({
      category: 'VALIDATION',
      code: 'AUTH_CALLBACK_CODE_MISSING',
      description: 'The Azure AD callback did not include an authorization code.',
      status: HttpStatus.BAD_REQUEST,
    }),
  cookieUserMissing: () =>
    new AppException({
      category: 'AUTH',
      code: 'AUTH_USER_MISSING',
      description: 'The authenticated user could not be resolved from the request.',
      status: HttpStatus.UNAUTHORIZED,
    }),
  forbiddenRole: () =>
    new AppException({
      category: 'AUTH',
      code: 'ROLE_FORBIDDEN',
      description: 'The current user does not have access to this resource.',
      status: HttpStatus.FORBIDDEN,
    }),
  tokenMissing: () =>
    new AppException({
      category: 'AUTH',
      code: 'AUTH_TOKEN_MISSING',
      description: 'Authentication is required to access this resource.',
      status: HttpStatus.UNAUTHORIZED,
    }),
};
