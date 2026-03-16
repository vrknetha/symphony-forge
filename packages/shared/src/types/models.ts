import type { DocType } from "../constants/document-templates";

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

export interface CreateProjectInput {
  description?: string;
  name: string;
}

export interface UpdateProjectInput {
  description?: string;
  name?: string;
  status?: "ACTIVE" | "ARCHIVED";
}

export interface CreateDocumentInput {
  docType: DocType;
  title: string;
}

export interface UpdateDocumentInput {
  docType?: DocType;
  title?: string;
}

export interface CreateAgentKeyInput {
  capabilities: string[];
  name: string;
}
