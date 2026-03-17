import { Injectable } from '@nestjs/common';
import type {
  AuthenticatedUser,
  ProjectMemberRecord as SharedProjectMemberRecord,
} from '@symphony/shared';
import type { MemberRole } from '@prisma/client';
import { ProjectAccessService } from './project-access.service';
import { projectErrors } from './projects.errors';
import { toProjectRecord } from './projects.mappers';
import { ProjectsRepository } from './projects.repository';
import type { AddProjectMemberDto } from './dto/add-project-member.dto';
import type { UpdateProjectMemberDto } from './dto/update-project-member.dto';

@Injectable()
export class ProjectMembersService {
  constructor(
    private readonly accessService: ProjectAccessService,
    private readonly repository: ProjectsRepository,
  ) {}

  async addMember(
    projectSlug: string,
    dto: AddProjectMemberDto,
    user: AuthenticatedUser,
  ): Promise<SharedProjectMemberRecord[]> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureWriteAccess(project, user);

    const memberUser = await this.repository.findUserByIdentity(dto.email, dto.azureOid);

    if (!memberUser) {
      throw projectErrors.userNotFound();
    }

    await this.repository.addMember(project.id, memberUser.id, dto.role as MemberRole);
    return (await this.listMembers(projectSlug, user)).members;
  }

  async listMembers(
    projectSlug: string,
    user: AuthenticatedUser,
  ): Promise<ReturnType<typeof toProjectRecord>> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureReadAccess(project, user);
    return toProjectRecord(project);
  }

  async removeMember(
    projectSlug: string,
    memberId: string,
    user: AuthenticatedUser,
  ): Promise<SharedProjectMemberRecord[]> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureWriteAccess(project, user);
    const member = await this.repository.findMemberById(memberId);

    if (!member || member.projectId !== project.id) {
      throw projectErrors.memberNotFound();
    }

    await this.repository.removeMember(memberId);
    return (await this.listMembers(projectSlug, user)).members;
  }

  async updateMember(
    projectSlug: string,
    memberId: string,
    dto: UpdateProjectMemberDto,
    user: AuthenticatedUser,
  ): Promise<SharedProjectMemberRecord[]> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureWriteAccess(project, user);
    const member = await this.repository.findMemberById(memberId);

    if (!member || member.projectId !== project.id) {
      throw projectErrors.memberNotFound();
    }

    await this.repository.updateMemberRole(memberId, dto.role as MemberRole);
    return (await this.listMembers(projectSlug, user)).members;
  }

  private async getProject(slug: string) {
    const project = await this.repository.findBySlug(slug);

    if (!project) {
      throw projectErrors.projectNotFound(slug);
    }

    return project;
  }
}
