import { createHash, randomBytes } from 'crypto';
import { Injectable } from '@nestjs/common';
import {
  AgentKeyResponseDto,
  CreatedAgentKeyResponseDto,
} from './dto/agent-key-response.dto';
import { CreateAgentKeyDto } from './dto/create-agent-key.dto';
import { AgentKeysRepository } from './agent-keys.repository';

@Injectable()
export class AgentKeysService {
  constructor(private readonly repository: AgentKeysRepository) {}

  async createAgentKey(
    dto: CreateAgentKeyDto,
  ): Promise<CreatedAgentKeyResponseDto> {
    const rawKey = `sk_${randomBytes(24).toString('hex')}`;
    const keyHash = createHash('sha256').update(rawKey).digest('hex');
    const keyPrefix = rawKey.slice(0, 10);
    const key = await this.repository.create({
      capabilities: dto.capabilities,
      keyHash,
      keyPrefix,
      name: dto.name,
    });
    return {
      active: key.active,
      capabilities: key.capabilities,
      id: key.id,
      keyPrefix: key.keyPrefix,
      lastUsedAt: key.lastUsedAt,
      name: key.name,
      rawKey,
    };
  }

  async listAgentKeys(): Promise<AgentKeyResponseDto[]> {
    const keys = await this.repository.list();
    return keys.map((key) => ({
      active: key.active,
      capabilities: key.capabilities,
      id: key.id,
      keyPrefix: key.keyPrefix,
      lastUsedAt: key.lastUsedAt,
      name: key.name,
    }));
  }

  async revokeAgentKey(id: string) {
    await this.repository.revoke(id);
    return { success: true };
  }
}
