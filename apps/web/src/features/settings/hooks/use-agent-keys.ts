import { useQuery } from '@tanstack/react-query'
import { listAgentKeys } from '../api/settings-api'

export function useAgentKeys() {
  return useQuery({
    queryFn: listAgentKeys,
    queryKey: ['agent-keys'],
    staleTime: 30_000,
  })
}
