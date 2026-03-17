import { type MemberRole, type ProjectStatus } from '@prisma/client';
import { toAuthenticatedUser } from '../auth/auth.mappers';
import type {
  ProjectMemberRecord as SharedProjectMemberRecord,
  ProjectRecord as SharedProjectRecord,
} from '@symphony/shared';
import type { ProjectRecord } from './projects.repository';

function toMemberRecord(
  member: ProjectRecord['members'][number],
): SharedProjectMemberRecord {
  return {
    id: member.id,
    joinedAt: member.createdAt.toISOString(),
    role: member.role as MemberRole,
    user: toAuthenticatedUser(member.user),
  };
}

export function toProjectRecord(project: ProjectRecord): SharedProjectRecord {
  return {
    description: project.description,
    documentCount: project.documents.length,
    id: project.id,
    members: project.members.map((member) => toMemberRecord(member)),
    name: project.name,
    owner: toAuthenticatedUser(project.owner),
    slug: project.slug,
    status: project.status as ProjectStatus,
    updatedAt: project.updatedAt.toISOString(),
  };
}
