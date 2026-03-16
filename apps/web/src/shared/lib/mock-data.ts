import {
  type AgentKeySummary,
  type AuthUser,
  type DocumentSummary,
  type ProjectDetail,
  type ProjectSummary,
} from "@symphony/shared";

export const mockUser: AuthUser = {
  email: "ravi@knacklabs.ai",
  id: "user-ravi",
  name: "Ravi Kiran",
  role: "ADMIN",
};

const projectDocuments: DocumentSummary[] = [
  {
    authorName: "Ravi Kiran",
    docType: "PLAN",
    id: "doc-plan",
    lastUpdated: "2026-03-16T16:00:00.000Z",
    proofDocSlug: "knack-forge-plan",
    slug: "v1-platform-plan",
    title: "V1 Platform Plan",
  },
  {
    authorName: "Maya Chen",
    docType: "SPEC",
    id: "doc-spec",
    lastUpdated: "2026-03-15T11:30:00.000Z",
    proofDocSlug: "proof-spec-shell",
    slug: "editor-embed-spec",
    title: "Editor Embed Spec",
  },
];

export const mockProjects: ProjectSummary[] = [
  {
    description:
      "Projects + Documents foundation for KnackLabs engineering work.",
    documentCount: projectDocuments.length,
    id: "project-forge",
    lastActive: projectDocuments[0].lastUpdated,
    name: "Knack Forge",
    slug: "knack-forge",
    status: "ACTIVE",
  },
];

export const mockProjectDetail: ProjectDetail = {
  ...mockProjects[0],
  documents: projectDocuments,
  members: [
    mockUser,
    {
      email: "maya@knacklabs.ai",
      id: "user-maya",
      name: "Maya Chen",
      role: "MEMBER",
    },
  ],
};

export const mockAgentKeys: AgentKeySummary[] = [
  {
    active: true,
    capabilities: ["read", "comment"],
    id: "agent-codex",
    keyPrefix: "codex-1a2b",
    lastUsedAt: "2026-03-16T09:15:00.000Z",
    name: "codex-worker",
  },
];
