import { Injectable } from '@nestjs/common';
import type {
  AgentKeyCapability,
  AgentKeyRecord as SharedAgentKeyRecord,
} from '@symphony/shared';
import { agentKeyErrors } from './agent-keys.errors';
import { toAgentKeyRecord } from './agent-keys.mappers';
import { AgentKeysRepository } from './agent-keys.repository';
import { buildAgentKeyMaterial, hashAgentKey } from './agent-keys.utils';
import type { CreateAgentKeyDto } from './dto/create-agent-key.dto';

interface CreatedAgentKeyResult extends SharedAgentKeyRecord {
  rawKey: string;
}

@Injectable()
export class AgentKeysService {
  constructor(private readonly repository: AgentKeysRepository) {}

  // CONVENTION_CONFLICT: PLAN.md models agent keys with bcrypt hashes, security.md requires SHA-256 at rest, chose SHA-256 because the security convention defines API key storage rules.
  async authenticate(rawKey: string): Promise<SharedAgentKeyRecord> {
    const hashedKey = hashAgentKey(rawKey);
    const agentKey = await this.repository.findActiveByHash(hashedKey);

    if (!agentKey) {
      throw agentKeyErrors.invalidKey();
    }

    await this.repository.touchLastUsed(agentKey.id);
    return toAgentKeyRecord(agentKey);
  }

  async create(dto: CreateAgentKeyDto): Promise<CreatedAgentKeyResult> {
    const material = buildAgentKeyMaterial();
    const agentKey = await this.repository.createKey({
      active: true,
      capabilities: dto.capabilities,
      keyHash: material.hash,
      keyPrefix: material.prefix,
      name: dto.name,
    });

    return {
      ...toAgentKeyRecord(agentKey),
      rawKey: material.rawKey,
    };
  }

  async list(): Promise<SharedAgentKeyRecord[]> {
    return (await this.repository.listKeys()).map((agentKey) => toAgentKeyRecord(agentKey));
  }

  async revoke(id: string): Promise<void> {
    const agentKey = await this.repository.findById(id);

    if (!agentKey) {
      throw agentKeyErrors.keyNotFound();
    }

    await this.repository.deactivate(id);
  }

  hasCapability(
    agentKey: SharedAgentKeyRecord,
    capability: AgentKeyCapability,
  ): boolean {
    return agentKey.capabilities.includes(capability);
  }
}
