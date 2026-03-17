import { zodResolver } from '@hookform/resolvers/zod'
import { useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/shared/components/Button'
import { Input } from '@/shared/components/Input'
import { Modal } from '@/shared/components/Modal'
import { slugify } from '@/shared/lib/slug'
import { useCreateProject } from '../hooks/use-create-project'

const projectSchema = z.object({
  description: z.string().trim().min(1, 'Add a short description.'),
  name: z.string().trim().min(2, 'Project name must be at least 2 characters.'),
})

interface NewProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (slug: string) => void
}

export function NewProjectModal({ isOpen, onClose, onCreated }: NewProjectModalProps) {
  const mutation = useCreateProject()
  const form = useForm<z.infer<typeof projectSchema>>({
    defaultValues: { description: '', name: '' },
    resolver: zodResolver(projectSchema),
  })
  const projectName = useWatch({ control: form.control, name: 'name' })
  const submit = form.handleSubmit((values) => void handleSubmit(values))

  async function handleSubmit(values: z.infer<typeof projectSchema>) {
    const project = await mutation.mutateAsync(values)
    form.reset()
    onClose()
    onCreated(project.slug)
  }

  return (
    <Modal
      description="Create a project shell and invite the first collaborators later."
      isOpen={isOpen}
      onClose={onClose}
      title="New project"
    >
      <form className="space-y-4" onSubmit={(event) => void submit(event)}>
        <label className="block text-sm font-medium">
          Name
          <Input className="mt-2" {...form.register('name')} placeholder="Knack Forge" />
        </label>
        <p className="text-xs text-muted-foreground">Slug preview: {slugify(projectName || 'new-project')}</p>
        <label className="block text-sm font-medium">
          Description
          <Input className="mt-2" {...form.register('description')} placeholder="What is this project for?" />
        </label>
        <p className="text-sm text-destructive">
          {form.formState.errors.name?.message ?? form.formState.errors.description?.message}
        </p>
        <div className="flex justify-end gap-3">
          <Button onClick={onClose} variant="ghost">
            Cancel
          </Button>
          <Button disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Creating…' : 'Create project'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
