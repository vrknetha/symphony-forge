import { Badge } from '@/shared/components/Badge'
import type { ProjectDetail } from '@/shared/types/models'

interface ProjectMembersCardProps {
  project: ProjectDetail
}

export function ProjectMembersCard({ project }: ProjectMembersCardProps) {
  return (
    <aside className="rounded-lg border border-border bg-surface p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-display text-2xl text-surface-foreground">Members</h2>
        <Badge tone="muted">{project.members.length}</Badge>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{project.description}</p>
      <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
        {project.members.map((member) => (
          <li key={member.id}>
            <p className="font-medium text-surface-foreground">{member.name}</p>
            <p>{member.email}</p>
          </li>
        ))}
      </ul>
    </aside>
  )
}
