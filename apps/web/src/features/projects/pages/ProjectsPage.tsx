import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '@/shared/components/Button'
import { Input } from '@/shared/components/Input'
import { PageHeader } from '@/shared/components/PageHeader'
import { Skeleton } from '@/shared/components/Skeleton'
import { NewProjectModal } from '../components/NewProjectModal'
import { ProjectCard } from '../components/ProjectCard'
import { useProjects } from '../hooks/use-projects'

export function ProjectsPage() {
  const navigate = useNavigate()
  const [isModalOpen, setModalOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const query = useProjects()
  const search = searchParams.get('q') ?? ''
  const projects = useMemo(
    () =>
      query.data?.filter((project) =>
        `${project.name} ${project.description}`.toLowerCase().includes(search.toLowerCase()),
      ) ?? [],
    [query.data, search],
  )

  function handleSearch(value: string) {
    const nextParams = new URLSearchParams(searchParams)

    if (value) {
      nextParams.set('q', value)
    } else {
      nextParams.delete('q')
    }

    setSearchParams(nextParams)
  }

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <>
            <Input onChange={(event) => handleSearch(event.target.value)} placeholder="Search projects" value={search} />
            <Button onClick={() => setModalOpen(true)}>New Project</Button>
          </>
        }
        eyebrow="Projects"
        subtitle="Browse active workspaces, search by project context, and jump straight into collaborative editing."
        title="Project Dashboard"
      />
      {query.isLoading ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : null}
      {query.error ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
          Failed to load projects. Check your connection and retry.
        </div>
      ) : null}
      {!query.isLoading && !query.error && projects.length === 0 ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
          No projects match the current filter. Try a different search or create a new project.
        </div>
      ) : null}
      {!query.isLoading && !query.error && projects.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      ) : null}
      <NewProjectModal
        isOpen={isModalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={(slug) => void navigate(`/projects/${slug}`)}
      />
    </section>
  )
}
