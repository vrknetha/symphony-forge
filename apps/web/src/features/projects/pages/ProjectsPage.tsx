import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/shared/components/PageHeader";
import { QueryState } from "@/shared/components/QueryState";
import { listProjects } from "../api/projects-api";
import { ProjectCard } from "../components/ProjectCard";

export function ProjectsPage() {
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const query = useQuery({ queryFn: listProjects, queryKey: ["projects"] });
  const projects =
    query.data?.filter((project) =>
      project.name.toLowerCase().includes(deferredSearch.toLowerCase()),
    ) ?? [];

  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <input
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search projects"
            value={search}
          />
        }
        eyebrow="Projects"
        subtitle="Browse active workspaces, check their latest document activity, and jump straight into collaborative editing."
        title="Project Dashboard"
      />
      <QueryState
        emptyMessage="No projects match the current filter."
        error={query.error}
        isEmpty={projects.length === 0}
        isLoading={query.isLoading}
      >
        <div className="grid gap-4 xl:grid-cols-2">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      </QueryState>
    </section>
  );
}
