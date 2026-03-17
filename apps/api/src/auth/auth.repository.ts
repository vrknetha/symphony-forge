import { Injectable } from '@nestjs/common';
import { Role, type User } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

interface UpsertUserInput {
  azureOid: string;
  email: string;
  name: string;
}

@Injectable()
export class AuthRepository {
  constructor(private readonly prisma: PrismaService) {}

  async findByAzureOid(azureOid: string): Promise<User | null> {
    return this.prisma.user.findUnique({ where: { azureOid } });
  }

  async upsertUser(input: UpsertUserInput): Promise<User> {
    return this.prisma.user.upsert({
      create: {
        azureOid: input.azureOid,
        email: input.email,
        name: input.name,
        role: Role.MEMBER,
      },
      update: {
        email: input.email,
        name: input.name,
      },
      where: { azureOid: input.azureOid },
    });
  }
}
