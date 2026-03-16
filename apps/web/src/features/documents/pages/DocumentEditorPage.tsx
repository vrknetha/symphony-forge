import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "@/shared/components/PageHeader";
import { QueryState } from "@/shared/components/QueryState";
import { getDocument } from "../api/documents-api";
import { EditorPlaceholder } from "../components/EditorPlaceholder";

export function DocumentEditorPage() {
  const { docSlug = "", slug = "" } = useParams();
  const query = useQuery({
    enabled: slug.length > 0 && docSlug.length > 0,
    queryFn: () => getDocument(slug, docSlug),
    queryKey: ["document", slug, docSlug],
  });

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <Link
            className="rounded-md border border-border px-4 py-2 text-sm text-foreground"
            to={`/projects/${slug}`}
          >
            Back to project
          </Link>
        }
        eyebrow="Document"
        subtitle="The page shell is ready for collaborative editing, metadata sidebars, and version history once Proof SDK is mounted."
        title={query.data?.title ?? "Document editor"}
      />
      <QueryState
        emptyMessage="Document not found."
        error={query.error}
        isEmpty={!query.data}
        isLoading={query.isLoading}
      >
        <EditorPlaceholder document={query.data!} />
      </QueryState>
    </section>
  );
}
