import { Link } from "react-router-dom";
import type { DocumentSummary } from "@/shared/types/models";

interface DocumentRowProps {
  projectSlug: string;
  summary: DocumentSummary;
}

export function DocumentRow({ projectSlug, summary }: DocumentRowProps) {
  return (
    <Link
      className="grid gap-2 rounded-md border border-border bg-background px-4 py-3 transition hover:border-primary/40"
      to={`/projects/${projectSlug}/docs/${summary.slug}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-foreground">{summary.title}</span>
        <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
          {summary.docType}
        </span>
      </div>
      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
        <span>{summary.authorName}</span>
        <span>{new Date(summary.lastUpdated).toLocaleString()}</span>
      </div>
    </Link>
  );
}
