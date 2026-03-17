import { appEnv } from '@/config/env'
import { apiClient } from '@/shared/lib/api-client'
import { mockListAgentKeys } from '@/shared/lib/mock-data'
import type { AgentKeySummary } from '@/shared/types/models'

export async function listAgentKeys() {
  if (appEnv.useMocks) {
    return mockListAgentKeys()
  }

  return apiClient.get<AgentKeySummary[]>('/agent-keys')
}
