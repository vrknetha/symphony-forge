import { Injectable } from '@nestjs/common';
import {
  MemberRole,
  Prisma,
  ProjectStatus,
  type ProjectMember,
  type User,
} from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

const projectInclude = {
  documents: {
    where: { deletedAt: null },
    select: { id: true },
  },
  members: {
    include: { user: true },
  },
  owner: true,
} satisfies Prisma.ProjectInclude;

export type ProjectRecord = Prisma.ProjectGetPayload<{
  include: typeof projectInclude;
}>;

@Injectable()
export class ProjectsRepository {
  constructor(private readonly prisma: PrismaService) {}

  async addMember(
    projectId: string,
    userId: string,
    role: MemberRole,
  ): Promise<ProjectMember> {
    return this.prisma.projectMember.upsert({
      create: { projectId, role, userId },
      update: { role },
      where: { projectId_userId: { projectId, userId } },
    });
  }

  async archiveProject(id: string): Promise<void> {
    await this.prisma.project.update({
      data: { deletedAt: new Date(), status: ProjectStatus.ARCHIVED },
      where: { id },
    });
  }

  async createProject(input: Prisma.ProjectUncheckedCreateInput): Promise<ProjectRecord> {
    return this.prisma.project.create({
      data: input,
      include: projectInclude,
    });
  }

  async findBySlug(slug: string): Promise<ProjectRecord | null> {
    return this.prisma.project.findFirst({
      include: projectInclude,
      where: { deletedAt: null, slug },
    });
  }

  async findMemberById(id: string): Promise<ProjectMember | null> {
    return this.prisma.projectMember.findUnique({ where: { id } });
  }

  async findProjectsForUser(userId: string, isAdmin: boolean): Promise<ProjectRecord[]> {
    return this.prisma.project.findMany({
      include: projectInclude,
      orderBy: { updatedAt: 'desc' },
      where: isAdmin
        ? { deletedAt: null }
        : {
            deletedAt: null,
            OR: [{ ownerId: userId }, { members: { some: { userId } } }],
          },
    });
  }

  async findUserByIdentity(email?: string, azureOid?: string): Promise<User | null> {
    if (email) {
      return this.prisma.user.findUnique({ where: { email } });
    }

    if (azureOid) {
      return this.prisma.user.findUnique({ where: { azureOid } });
    }

    return null;
  }

  async removeMember(id: string): Promise<void> {
    await this.prisma.projectMember.delete({ where: { id } });
  }

  async updateMemberRole(id: string, role: MemberRole): Promise<ProjectMember> {
    return this.prisma.projectMember.update({
      data: { role },
      where: { id },
    });
  }

  async updateProject(
    id: string,
    data: Prisma.ProjectUncheckedUpdateInput,
  ): Promise<ProjectRecord> {
    return this.prisma.project.update({
      data,
      include: projectInclude,
      where: { id },
    });
  }
}
