import { Link } from "react-router-dom";
import type { ProjectSummary } from "@/shared/types/models";

interface ProjectCardProps {
  project: ProjectSummary;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link
      className="rounded-lg border border-border bg-surface p-5 transition hover:-translate-y-0.5 hover:border-primary/40"
      to={`/projects/${project.slug}`}
    >
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
        {project.status}
      </p>
      <h2 className="mt-3 font-display text-2xl text-surface-foreground">
        {project.name}
      </h2>
      <p className="mt-3 text-sm text-muted-foreground">
        {project.description}
      </p>
      <div className="mt-5 flex items-center justify-between text-sm text-muted-foreground">
        <span>{project.documentCount} docs</span>
        <span>{new Date(project.lastActive).toLocaleDateString()}</span>
      </div>
    </Link>
  );
}
