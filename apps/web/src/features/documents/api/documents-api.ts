import { appEnv } from "@/config/env";
import { apiClient } from "@/shared/lib/api-client";
import { mockProjectDetail } from "@/shared/lib/mock-data";
import type { DocumentSummary } from "@/shared/types/models";

export async function getDocument(
  projectSlug: string,
  docSlug: string,
): Promise<DocumentSummary> {
  if (appEnv.useMocks) {
    const document = mockProjectDetail.documents.find(
      (item) => item.slug === docSlug,
    );
    return (
      document ?? {
        ...mockProjectDetail.documents[0],
        proofDocSlug: `${projectSlug}-${docSlug}`,
        slug: docSlug,
      }
    );
  }

  return apiClient.get<DocumentSummary>(
    `/projects/${projectSlug}/documents/${docSlug}`,
  );
}
