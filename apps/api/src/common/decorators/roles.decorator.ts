import { SetMetadata } from '@nestjs/common';
import type { UserRole } from '@symphony/shared';

export const ROLES_KEY = 'required-roles';
export const Roles = (...roles: UserRole[]) => SetMetadata(ROLES_KEY, roles);
