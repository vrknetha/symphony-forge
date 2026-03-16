import { HttpStatus } from '@nestjs/common';
import { AppException } from '../common/errors/app-exception';

export function createProjectError(
  code: string,
  category: 'authorization' | 'business',
  description: string,
  status: HttpStatus,
) {
  return new AppException({
    category,
    code,
    description,
    message: description,
    retryable: false,
    status,
  });
}
