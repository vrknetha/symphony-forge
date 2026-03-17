import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProject } from '../api/projects-api'
import { projectKeys } from '../api/project-keys'

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}
