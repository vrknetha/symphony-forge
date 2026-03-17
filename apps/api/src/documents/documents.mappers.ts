import { type DocType } from '@prisma/client';
import type { DocumentRecord as SharedDocumentRecord } from '@symphony/shared';
import { toAuthenticatedUser } from '../auth/auth.mappers';
import type { DocumentRecord } from './documents.repository';
import { ProofClient } from './proof.client';

export function toDocumentRecord(
  document: DocumentRecord,
  proofClient: ProofClient,
): SharedDocumentRecord {
  return {
    createdAt: document.createdAt.toISOString(),
    createdBy: toAuthenticatedUser(document.createdBy),
    docType: document.docType as DocType,
    editorUrl: proofClient.buildEditorUrl(document.project.slug, document.slug),
    id: document.id,
    projectSlug: document.project.slug,
    slug: document.slug,
    title: document.title,
    updatedAt: document.updatedAt.toISOString(),
  };
}
