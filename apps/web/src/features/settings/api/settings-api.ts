import { appEnv } from "@/config/env";
import { apiClient } from "@/shared/lib/api-client";
import { mockAgentKeys } from "@/shared/lib/mock-data";
import type { AgentKeySummary } from "@/shared/types/models";

export async function listAgentKeys(): Promise<AgentKeySummary[]> {
  if (appEnv.useMocks) {
    return mockAgentKeys;
  }

  return apiClient.get<AgentKeySummary[]>("/agent-keys");
}
