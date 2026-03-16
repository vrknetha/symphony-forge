import { Role } from '@prisma/client';

export interface AuthenticatedUser {
  authType: 'agent' | 'human';
  capabilities: string[];
  email: string;
  id: string;
  name: string;
  role: Role;
  azureOid: string | null;
}
