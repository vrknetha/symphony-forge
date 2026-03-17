import { useMutation, useQueryClient } from '@tanstack/react-query'
import { documentKeys } from '../api/document-keys'
import { createDocument } from '../api/documents-api'

export function useCreateDocument(projectSlug: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: Parameters<typeof createDocument>[1]) => createDocument(projectSlug, input),
    onSuccess: (document) => {
      void queryClient.invalidateQueries({ queryKey: documentKeys.list(projectSlug) })
      void queryClient.invalidateQueries({
        queryKey: documentKeys.detail(projectSlug, document.slug),
      })
    },
  })
}
