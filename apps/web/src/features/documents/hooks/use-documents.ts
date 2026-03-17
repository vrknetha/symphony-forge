import { useQuery } from '@tanstack/react-query'
import { documentKeys } from '../api/document-keys'
import { listDocuments } from '../api/documents-api'

export function useDocuments(projectSlug: string) {
  return useQuery({
    enabled: projectSlug.length > 0,
    queryFn: () => listDocuments(projectSlug),
    queryKey: documentKeys.list(projectSlug),
    staleTime: 30_000,
  })
}
