import { AgentKey, Role, User } from '@prisma/client';
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

interface UpsertUserInput {
  azureOid: string;
  email: string;
  name: string;
  role: Role;
}

@Injectable()
export class AuthRepository {
  constructor(private readonly prisma: PrismaService) {}

  findActiveAgentKeyByHash(keyHash: string): Promise<AgentKey | null> {
    return this.prisma.agentKey.findFirst({
      where: { active: true, keyHash },
    });
  }

  touchAgentKey(id: string): Promise<AgentKey> {
    return this.prisma.agentKey.update({
      data: { lastUsedAt: new Date() },
      where: { id },
    });
  }

  upsertUser(input: UpsertUserInput): Promise<User> {
    return this.prisma.user.upsert({
      create: input,
      update: {
        email: input.email,
        name: input.name,
        role: input.role,
      },
      where: { azureOid: input.azureOid },
    });
  }
}
