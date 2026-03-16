import { MemberRole, ProjectStatus, Role } from '@prisma/client';
import {
  ProjectMemberResponseDto,
  ProjectResponseDto,
} from './dto/project-response.dto';

interface ProjectSummary {
  _count: { documents: number };
  description: string | null;
  id: string;
  name: string;
  owner: { name: string };
  ownerId: string;
  slug: string;
  status: ProjectStatus;
}

interface ProjectMemberSummary {
  id: string;
  role: MemberRole;
  user: { email: string; name: string; role: Role };
  userId: string;
}

export function toProject(project: ProjectSummary): ProjectResponseDto {
  return {
    description: project.description,
    documentCount: project._count.documents,
    id: project.id,
    name: project.name,
    ownerId: project.ownerId,
    ownerName: project.owner.name,
    slug: project.slug,
    status: project.status,
  };
}

export function toProjectMember(
  member: ProjectMemberSummary,
): ProjectMemberResponseDto {
  return {
    email: member.user.email,
    id: member.id,
    memberRole: member.role,
    name: member.user.name,
    role: member.user.role,
    userId: member.userId,
  };
}
