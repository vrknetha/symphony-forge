import { Link } from 'react-router-dom'
import { Badge } from '@/shared/components/Badge'
import { formatDateTime } from '@/shared/lib/date'
import type { DocumentSummary } from '@/shared/types/models'

interface DocumentRowProps {
  projectSlug: string
  summary: DocumentSummary
}

export function DocumentRow({ projectSlug, summary }: DocumentRowProps) {
  return (
    <Link
      className="grid gap-2 rounded-md border border-border bg-background px-4 py-3 transition hover:border-primary/40"
      to={`/projects/${projectSlug}/docs/${summary.slug}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-foreground">{summary.title}</span>
        <Badge>{summary.docType}</Badge>
      </div>
      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
        <span>{summary.authorName}</span>
        <span>{formatDateTime(summary.lastUpdated)}</span>
      </div>
    </Link>
  )
}
