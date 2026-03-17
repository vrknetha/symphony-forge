import { useQuery } from '@tanstack/react-query'
import { projectKeys } from '../api/project-keys'
import { listProjects } from '../api/projects-api'

export function useProjects() {
  return useQuery({
    queryFn: listProjects,
    queryKey: projectKeys.list(),
    staleTime: 60_000,
  })
}
