import type {
  AGENT_KEY_CAPABILITIES,
  DOC_TYPES,
  MEMBER_ROLES,
  PROJECT_STATUSES,
  USER_ROLES,
} from '../constants/domain.constants';

export type UserRole = (typeof USER_ROLES)[number];
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];
export type MemberRole = (typeof MEMBER_ROLES)[number];
export type DocType = (typeof DOC_TYPES)[number];
export type AgentKeyCapability = (typeof AGENT_KEY_CAPABILITIES)[number];

export interface AuthenticatedUser {
  azureOid: string;
  email: string;
  id: string;
  name: string;
  role: UserRole;
}

export interface ProjectMemberRecord {
  id: string;
  joinedAt: string;
  role: MemberRole;
  user: AuthenticatedUser;
}

export interface ProjectRecord {
  description: string | null;
  documentCount: number;
  id: string;
  members: ProjectMemberRecord[];
  name: string;
  owner: AuthenticatedUser;
  slug: string;
  status: ProjectStatus;
  updatedAt: string;
}

export interface DocumentRecord {
  createdAt: string;
  createdBy: AuthenticatedUser;
  docType: DocType;
  editorUrl: string;
  id: string;
  projectSlug: string;
  slug: string;
  title: string;
  updatedAt: string;
}

export interface AgentKeyRecord {
  active: boolean;
  capabilities: AgentKeyCapability[];
  createdAt: string;
  id: string;
  keyPrefix: string;
  lastUsedAt: string | null;
  name: string;
}
