import { HttpStatus } from '@nestjs/common';
import { AppException } from '../common/errors/app-exception';

export const projectErrors = {
  memberNotFound: () =>
    new AppException({
      category: 'NOT_FOUND',
      code: 'PROJECT_MEMBER_NOT_FOUND',
      description: 'The requested project member could not be found.',
      status: HttpStatus.NOT_FOUND,
    }),
  projectNotFound: (slug: string) =>
    new AppException({
      category: 'NOT_FOUND',
      code: 'PROJECT_NOT_FOUND',
      description: `Project '${slug}' was not found.`,
      status: HttpStatus.NOT_FOUND,
    }),
  slugConflict: (slug: string) =>
    new AppException({
      category: 'CONFLICT',
      code: 'PROJECT_SLUG_TAKEN',
      description: `A project with slug '${slug}' already exists.`,
      status: HttpStatus.CONFLICT,
    }),
  userForbidden: () =>
    new AppException({
      category: 'AUTH',
      code: 'PROJECT_ACCESS_FORBIDDEN',
      description: 'The current user cannot access this project.',
      status: HttpStatus.FORBIDDEN,
    }),
  userNotFound: () =>
    new AppException({
      category: 'NOT_FOUND',
      code: 'PROJECT_MEMBER_USER_NOT_FOUND',
      description: 'The requested user does not exist in Symphony Forge yet.',
      status: HttpStatus.NOT_FOUND,
    }),
};
