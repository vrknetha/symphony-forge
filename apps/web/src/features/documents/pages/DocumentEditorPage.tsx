import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useProject } from '@/features/projects/hooks/use-project'
import { Badge } from '@/shared/components/Badge'
import { PageHeader } from '@/shared/components/PageHeader'
import { Skeleton } from '@/shared/components/Skeleton'
import { EditorPlaceholder } from '../components/EditorPlaceholder'
import { useDocument } from '../hooks/use-document'

export function DocumentEditorPage() {
  const [isSidebarOpen, setSidebarOpen] = useState(true)
  const { docSlug = '', slug = '' } = useParams()
  const projectQuery = useProject(slug)
  const documentQuery = useDocument(slug, docSlug)

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <>
            <Badge tone="muted">{projectQuery.data?.name ?? 'Project'}</Badge>
            <Link className="rounded-md border border-border px-4 py-2 text-sm" to={`/projects/${slug}`}>
              Back to project
            </Link>
          </>
        }
        eyebrow="Document"
        subtitle="The editor shell is ready for collaborative editing, metadata sidebars, and Proof SDK token handoff."
        title={documentQuery.data?.title ?? 'Document editor'}
      />
      {projectQuery.isLoading || documentQuery.isLoading ? <Skeleton className="h-[32rem]" /> : null}
      {projectQuery.error || documentQuery.error ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
          Failed to load this document. Check your connection and retry.
        </div>
      ) : null}
      {!projectQuery.isLoading && !documentQuery.isLoading && documentQuery.data ? (
        <EditorPlaceholder
          document={documentQuery.data}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setSidebarOpen((value) => !value)}
        />
      ) : null}
    </section>
  )
}
