import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/shared/components/Button'
import { Input } from '@/shared/components/Input'
import { Modal } from '@/shared/components/Modal'
import { Select } from '@/shared/components/Select'
import { docTypes } from '@/shared/types/models'
import { useCreateDocument } from '../hooks/use-create-document'

const documentSchema = z.object({
  docType: z.enum(docTypes),
  title: z.string().trim().min(2, 'Document title must be at least 2 characters.'),
})

interface NewDocumentModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (docSlug: string) => void
  projectSlug: string
}

export function NewDocumentModal({
  isOpen,
  onClose,
  onCreated,
  projectSlug,
}: NewDocumentModalProps) {
  const mutation = useCreateDocument(projectSlug)
  const form = useForm<z.infer<typeof documentSchema>>({
    defaultValues: { docType: 'PLAN', title: '' },
    resolver: zodResolver(documentSchema),
  })
  const submit = form.handleSubmit((values) => void handleSubmit(values))

  async function handleSubmit(values: z.infer<typeof documentSchema>) {
    const document = await mutation.mutateAsync(values)
    form.reset()
    onClose()
    onCreated(document.slug)
  }

  return (
    <Modal
      description="Create a collaborative Proof-backed document inside this project."
      isOpen={isOpen}
      onClose={onClose}
      title="New document"
    >
      <form className="space-y-4" onSubmit={(event) => void submit(event)}>
        <label className="block text-sm font-medium">
          Title
          <Input className="mt-2" {...form.register('title')} placeholder="Platform rollout plan" />
        </label>
        <label className="block text-sm font-medium">
          Type
          <Select className="mt-2" {...form.register('docType')}>
            {docTypes.map((docType) => (
              <option key={docType} value={docType}>
                {docType}
              </option>
            ))}
          </Select>
        </label>
        <p className="text-sm text-destructive">{form.formState.errors.title?.message}</p>
        <div className="flex justify-end gap-3">
          <Button onClick={onClose} variant="ghost">
            Cancel
          </Button>
          <Button disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Creating…' : 'Create document'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
