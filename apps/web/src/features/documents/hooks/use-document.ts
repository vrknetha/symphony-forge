import { useQuery } from '@tanstack/react-query'
import { documentKeys } from '../api/document-keys'
import { getDocument } from '../api/documents-api'

export function useDocument(projectSlug: string, docSlug: string) {
  return useQuery({
    enabled: projectSlug.length > 0 && docSlug.length > 0,
    queryFn: () => getDocument(projectSlug, docSlug),
    queryKey: documentKeys.detail(projectSlug, docSlug),
    staleTime: 30_000,
  })
}
