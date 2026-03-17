import type { AgentKeyRecord as SharedAgentKeyRecord } from '@symphony/shared';
import type { AgentKey } from '@prisma/client';

export function toAgentKeyRecord(agentKey: AgentKey): SharedAgentKeyRecord {
  return {
    active: agentKey.active,
    capabilities: agentKey.capabilities,
    createdAt: agentKey.createdAt.toISOString(),
    id: agentKey.id,
    keyPrefix: agentKey.keyPrefix,
    lastUsedAt: agentKey.lastUsedAt?.toISOString() ?? null,
    name: agentKey.name,
  };
}
