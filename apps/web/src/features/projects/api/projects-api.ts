import { appEnv } from "@/config/env";
import { apiClient } from "@/shared/lib/api-client";
import { mockProjectDetail, mockProjects } from "@/shared/lib/mock-data";
import type { ProjectDetail, ProjectSummary } from "@symphony/shared";

export async function getProject(slug: string): Promise<ProjectDetail> {
  if (appEnv.useMocks) {
    return { ...mockProjectDetail, slug };
  }

  return apiClient.get<ProjectDetail>(`/projects/${slug}`);
}

export async function listProjects(): Promise<ProjectSummary[]> {
  if (appEnv.useMocks) {
    return mockProjects;
  }

  return apiClient.get<ProjectSummary[]>("/projects");
}
