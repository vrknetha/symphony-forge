import { MemberRole, ProjectStatus } from '@prisma/client';
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

interface ProjectFilters {
  search?: string;
  status?: ProjectStatus;
}

@Injectable()
export class ProjectsRepository {
  constructor(private readonly prisma: PrismaService) {}

  addMember(projectId: string, role: MemberRole, userId: string) {
    return this.prisma.projectMember.create({
      data: { projectId, role, userId },
    });
  }

  archiveProject(id: string) {
    return this.prisma.project.update({
      data: { deletedAt: new Date(), status: ProjectStatus.ARCHIVED },
      where: { id },
    });
  }

  createProject(
    description: string | undefined,
    name: string,
    ownerId: string,
    slug: string,
  ) {
    return this.prisma.project.create({
      data: {
        description,
        members: { create: { role: MemberRole.OWNER, userId: ownerId } },
        name,
        ownerId,
        slug,
      },
      include: { _count: { select: { documents: true } }, owner: true },
    });
  }

  findAccessibleProject(slug: string, userId: string) {
    return this.prisma.project.findFirst({
      include: {
        _count: { select: { documents: { where: { deletedAt: null } } } },
        members: { include: { user: true } },
        owner: true,
      },
      where: {
        deletedAt: null,
        slug,
        OR: [{ ownerId: userId }, { members: { some: { userId } } }],
      },
    });
  }

  findMember(projectId: string, memberId: string) {
    return this.prisma.projectMember.findFirst({
      include: { user: true },
      where: { id: memberId, projectId },
    });
  }

  findProjectBySlug(slug: string) {
    return this.prisma.project.findFirst({ where: { deletedAt: null, slug } });
  }

  findUserByIdentifier(azureOid?: string, email?: string) {
    return this.prisma.user.findFirst({
      where: azureOid
        ? { azureOid }
        : email
          ? { email }
          : { id: '__missing__' },
    });
  }

  listMembers(projectId: string) {
    return this.prisma.projectMember.findMany({
      include: { user: true },
      orderBy: { createdAt: 'asc' },
      where: { projectId },
    });
  }

  listProjects(filters: ProjectFilters, userId: string) {
    return this.prisma.project.findMany({
      include: {
        _count: { select: { documents: { where: { deletedAt: null } } } },
        owner: true,
      },
      orderBy: { updatedAt: 'desc' },
      where: {
        deletedAt: null,
        name: filters.search
          ? { contains: filters.search, mode: 'insensitive' }
          : undefined,
        OR: [{ ownerId: userId }, { members: { some: { userId } } }],
        status: filters.status,
      },
    });
  }

  removeMember(id: string) {
    return this.prisma.projectMember.delete({ where: { id } });
  }

  updateMember(id: string, role: MemberRole) {
    return this.prisma.projectMember.update({ data: { role }, where: { id } });
  }

  updateProject(
    id: string,
    data: {
      description?: string;
      name?: string;
      slug?: string;
      status?: ProjectStatus;
    },
  ) {
    return this.prisma.project.update({
      data,
      include: {
        _count: { select: { documents: { where: { deletedAt: null } } } },
        owner: true,
      },
      where: { id },
    });
  }
}
