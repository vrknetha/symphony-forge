import { Injectable } from '@nestjs/common';
import type { AgentKey, Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class AgentKeysRepository {
  constructor(private readonly prisma: PrismaService) {}

  async createKey(data: Prisma.AgentKeyUncheckedCreateInput): Promise<AgentKey> {
    return this.prisma.agentKey.create({ data });
  }

  async deactivate(id: string): Promise<void> {
    await this.prisma.agentKey.update({
      data: { active: false },
      where: { id },
    });
  }

  async findActiveByHash(keyHash: string): Promise<AgentKey | null> {
    return this.prisma.agentKey.findFirst({
      where: { active: true, keyHash },
    });
  }

  async findById(id: string): Promise<AgentKey | null> {
    return this.prisma.agentKey.findUnique({ where: { id } });
  }

  async listKeys(): Promise<AgentKey[]> {
    return this.prisma.agentKey.findMany({
      orderBy: { createdAt: 'desc' },
    });
  }

  async touchLastUsed(id: string): Promise<void> {
    await this.prisma.agentKey.update({
      data: { lastUsedAt: new Date() },
      where: { id },
    });
  }
}
