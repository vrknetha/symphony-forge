// CONVENTION_CONFLICT: architecture.md routes shared types through packages/shared, but this isolated web-only scaffold cannot modify packages/shared.
export const docTypes = [
  "PLAN",
  "SPEC",
  "ADR",
  "NOTES",
  "RETROSPECTIVE",
] as const;
export type DocType = (typeof docTypes)[number];

export interface AuthUser {
  email: string;
  id: string;
  name: string;
  role: "ADMIN" | "MEMBER";
}

export interface DocumentSummary {
  authorName: string;
  docType: DocType;
  id: string;
  lastUpdated: string;
  proofDocSlug: string;
  slug: string;
  title: string;
}

export interface ProjectSummary {
  description: string;
  documentCount: number;
  id: string;
  lastActive: string;
  name: string;
  slug: string;
  status: "ACTIVE" | "ARCHIVED";
}

export interface ProjectDetail extends ProjectSummary {
  documents: DocumentSummary[];
  members: AuthUser[];
}

export interface AgentKeySummary {
  active: boolean;
  capabilities: string[];
  id: string;
  keyPrefix: string;
  lastUsedAt: string | null;
  name: string;
}
