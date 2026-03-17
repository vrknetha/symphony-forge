import type { User } from '@prisma/client';
import type { AuthenticatedUser } from '@symphony/shared';

export function toAuthenticatedUser(user: User): AuthenticatedUser {
  return {
    azureOid: user.azureOid,
    email: user.email,
    id: user.id,
    name: user.name,
    role: user.role,
  };
}
