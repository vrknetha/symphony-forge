import { useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { NewDocumentModal } from '@/features/documents/components/NewDocumentModal'
import { useDocuments } from '@/features/documents/hooks/use-documents'
import { Button } from '@/shared/components/Button'
import { PageHeader } from '@/shared/components/PageHeader'
import { Skeleton } from '@/shared/components/Skeleton'
import { DocumentRow } from '../components/DocumentRow'
import { ProjectFilters } from '../components/ProjectFilters'
import { ProjectMembersCard } from '../components/ProjectMembersCard'
import { useProject } from '../hooks/use-project'

export function ProjectDetailPage() {
  const navigate = useNavigate()
  const { slug = '' } = useParams()
  const [isModalOpen, setModalOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const projectQuery = useProject(slug)
  const documentsQuery = useDocuments(slug)
  const search = searchParams.get('q') ?? ''
  const type = searchParams.get('type') ?? 'ALL'
  const documents = useMemo(
    () =>
      documentsQuery.data?.filter((document) => {
        const matchesSearch = document.title.toLowerCase().includes(search.toLowerCase())
        const matchesType = type === 'ALL' || document.docType === type
        return matchesSearch && matchesType
      }) ?? [],
    [documentsQuery.data, search, type],
  )

  function updateFilter(key: 'q' | 'type', value: string) {
    const nextParams = new URLSearchParams(searchParams)

    if (!value || value === 'ALL') {
      nextParams.delete(key)
    } else {
      nextParams.set(key, value)
    }

    setSearchParams(nextParams)
  }

  return (
    <section className="space-y-6">
      <PageHeader
        actions={<Button onClick={() => setModalOpen(true)}>New Document</Button>}
        eyebrow="Project"
        subtitle="Manage document creation, filter by type, and keep membership context close to the work."
        title={projectQuery.data?.name ?? 'Project detail'}
      />
      <ProjectFilters
        onSearchChange={(value) => updateFilter('q', value)}
        onTypeChange={(value) => updateFilter('type', value)}
        search={search}
        type={type}
      />
      {projectQuery.isLoading || documentsQuery.isLoading ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      ) : null}
      {projectQuery.error || documentsQuery.error ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
          Failed to load this project. Check your connection and retry.
        </div>
      ) : null}
      {!projectQuery.isLoading && !documentsQuery.isLoading && projectQuery.data ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <div className="space-y-3">
            {documents.length === 0 ? (
              <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
                No documents match the current filters.
              </div>
            ) : (
              documents.map((document) => (
                <DocumentRow key={document.id} projectSlug={slug} summary={document} />
              ))
            )}
          </div>
          <ProjectMembersCard project={projectQuery.data} />
        </div>
      ) : null}
      <NewDocumentModal
        isOpen={isModalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={(docSlug) => void navigate(`/projects/${slug}/docs/${docSlug}`)}
        projectSlug={slug}
      />
    </section>
  )
}
