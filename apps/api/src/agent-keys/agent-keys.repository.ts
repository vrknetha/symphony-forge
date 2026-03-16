import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class AgentKeysRepository {
  constructor(private readonly prisma: PrismaService) {}

  create(data: {
    capabilities: string[];
    keyHash: string;
    keyPrefix: string;
    name: string;
  }) {
    return this.prisma.agentKey.create({ data });
  }

  list() {
    return this.prisma.agentKey.findMany({ orderBy: { createdAt: 'desc' } });
  }

  revoke(id: string) {
    return this.prisma.agentKey.update({
      data: { active: false },
      where: { id },
    });
  }
}
