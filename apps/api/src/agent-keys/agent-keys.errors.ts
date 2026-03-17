import { HttpStatus } from '@nestjs/common';
import { AppException } from '../common/errors/app-exception';

export const agentKeyErrors = {
  invalidKey: () =>
    new AppException({
      category: 'AUTH',
      code: 'AGENT_KEY_INVALID',
      description: 'The supplied agent API key is invalid or inactive.',
      status: HttpStatus.UNAUTHORIZED,
    }),
  keyNotFound: () =>
    new AppException({
      category: 'NOT_FOUND',
      code: 'AGENT_KEY_NOT_FOUND',
      description: 'The requested agent API key does not exist.',
      status: HttpStatus.NOT_FOUND,
    }),
};
