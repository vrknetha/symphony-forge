import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { QueryState } from "@/shared/components/QueryState";
import { getProject } from "../api/projects-api";
import { DocumentRow } from "../components/DocumentRow";

export function ProjectDetailPage() {
  const { slug = "" } = useParams();
  const query = useQuery({
    enabled: slug.length > 0,
    queryFn: () => getProject(slug),
    queryKey: ["project", slug],
  });

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <Link
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
            to={`/projects/${slug}/docs/v1-platform-plan`}
          >
            Open latest document
          </Link>
        }
        eyebrow="Project"
        subtitle="Manage document creation, filter by type, and keep membership context close to the work."
        title={query.data?.name ?? "Project detail"}
      />
      <QueryState
        emptyMessage="This project does not have any documents yet."
        error={query.error}
        isEmpty={(query.data?.documents.length ?? 0) === 0}
        isLoading={query.isLoading}
      >
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <div className="space-y-3">
            {query.data?.documents.map((document) => (
              <DocumentRow
                key={document.id}
                projectSlug={slug}
                summary={document}
              />
            ))}
          </div>
          <aside className="rounded-lg border border-border bg-surface p-5">
            <h2 className="font-display text-2xl text-surface-foreground">
              Members
            </h2>
            <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
              {query.data?.members.map((member) => (
                <li key={member.id}>
                  <p className="font-medium text-surface-foreground">
                    {member.name}
                  </p>
                  <p>{member.email}</p>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </QueryState>
    </section>
  );
}
