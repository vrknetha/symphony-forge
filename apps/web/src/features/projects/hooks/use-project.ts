import { useQuery } from '@tanstack/react-query'
import { getProject } from '../api/projects-api'
import { projectKeys } from '../api/project-keys'

export function useProject(slug: string) {
  return useQuery({
    enabled: slug.length > 0,
    queryFn: () => getProject(slug),
    queryKey: projectKeys.detail(slug),
    staleTime: 60_000,
  })
}
