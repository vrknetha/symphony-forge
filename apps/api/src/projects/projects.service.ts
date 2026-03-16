import { HttpStatus, Injectable } from '@nestjs/common';
import { MemberRole, Role } from '@prisma/client';
import { AuthenticatedUser } from '../common/types/authenticated-user';
import { toSlug } from '../common/utils/slug';
import {
  AddProjectMemberDto,
  UpdateProjectMemberDto,
} from './dto/project-member.dto';
import {
  ProjectDetailResponseDto,
  ProjectMemberResponseDto,
  ProjectResponseDto,
} from './dto/project-response.dto';
import { CreateProjectDto } from './dto/create-project.dto';
import { ListProjectsQueryDto } from './dto/list-projects-query.dto';
import { UpdateProjectDto } from './dto/update-project.dto';
import { createProjectError } from './projects.errors';
import { toProject, toProjectMember } from './projects.mappers';
import { ProjectsRepository } from './projects.repository';

@Injectable()
export class ProjectsService {
  constructor(private readonly repository: ProjectsRepository) {}

  async addMember(
    dto: AddProjectMemberDto,
    slug: string,
    user: AuthenticatedUser,
  ): Promise<ProjectMemberResponseDto> {
    const project = await this.requireOwnerProject(slug, user);
    const target = await this.repository.findUserByIdentifier(
      dto.azureOid,
      dto.email,
    );
    if (!target) {
      throw createProjectError(
        'USER_NOT_FOUND',
        'business',
        'The requested user could not be found.',
        HttpStatus.NOT_FOUND,
      );
    }
    const member = await this.repository.addMember(
      project.id,
      dto.role,
      target.id,
    );
    return toProjectMember({
      id: member.id,
      role: member.role,
      user: target,
      userId: target.id,
    });
  }

  async archiveProject(slug: string, user: AuthenticatedUser) {
    const project = await this.requireOwnerProject(slug, user);
    await this.repository.archiveProject(project.id);
    return { success: true };
  }

  async createProject(
    dto: CreateProjectDto,
    user: AuthenticatedUser,
  ): Promise<ProjectResponseDto> {
    const slug = toSlug(dto.name);
    const existing = await this.repository.findProjectBySlug(slug);
    if (existing) {
      throw createProjectError(
        'PROJECT_SLUG_CONFLICT',
        'business',
        'A project already exists with this slug.',
        HttpStatus.CONFLICT,
      );
    }
    const project = await this.repository.createProject(
      dto.description,
      dto.name,
      user.id,
      slug,
    );
    return toProject(project);
  }

  async getProject(
    slug: string,
    user: AuthenticatedUser,
  ): Promise<ProjectDetailResponseDto> {
    const project = await this.requireProject(slug, user);
    return {
      ...toProject(project),
      members: project.members.map((member) => toProjectMember(member)),
    };
  }

  async listMembers(
    slug: string,
    user: AuthenticatedUser,
  ): Promise<ProjectMemberResponseDto[]> {
    const project = await this.requireProject(slug, user);
    const members = await this.repository.listMembers(project.id);
    return members.map((member) => toProjectMember(member));
  }

  async listProjects(
    query: ListProjectsQueryDto,
    user: AuthenticatedUser,
  ): Promise<ProjectResponseDto[]> {
    const projects = await this.repository.listProjects(query, user.id);
    return projects.map((project) => toProject(project));
  }

  async removeMember(memberId: string, slug: string, user: AuthenticatedUser) {
    const project = await this.requireOwnerProject(slug, user);
    const member = await this.repository.findMember(project.id, memberId);
    if (!member || member.role === MemberRole.OWNER) {
      throw createProjectError(
        'MEMBER_NOT_FOUND',
        'business',
        'The requested project member was not found.',
        HttpStatus.NOT_FOUND,
      );
    }
    await this.repository.removeMember(member.id);
    return { success: true };
  }

  async updateMember(
    memberId: string,
    dto: UpdateProjectMemberDto,
    slug: string,
    user: AuthenticatedUser,
  ) {
    const project = await this.requireOwnerProject(slug, user);
    const member = await this.repository.findMember(project.id, memberId);
    if (!member) {
      throw createProjectError(
        'MEMBER_NOT_FOUND',
        'business',
        'The requested project member was not found.',
        HttpStatus.NOT_FOUND,
      );
    }
    const updated = await this.repository.updateMember(member.id, dto.role);
    return toProjectMember({
      id: updated.id,
      role: updated.role,
      user: member.user,
      userId: member.userId,
    });
  }

  async updateProject(
    dto: UpdateProjectDto,
    slug: string,
    user: AuthenticatedUser,
  ): Promise<ProjectResponseDto> {
    const project = await this.requireOwnerProject(slug, user);
    const nextSlug = dto.name ? toSlug(dto.name) : undefined;
    const updated = await this.repository.updateProject(project.id, {
      description: dto.description,
      name: dto.name,
      slug: nextSlug,
      status: dto.status,
    });
    return toProject(updated);
  }

  private async requireOwnerProject(slug: string, user: AuthenticatedUser) {
    const project = await this.requireProject(slug, user);
    const isOwner = project.ownerId === user.id || user.role === Role.ADMIN;
    if (!isOwner) {
      throw createProjectError(
        'PROJECT_FORBIDDEN',
        'authorization',
        'Only project owners or admins can mutate this project.',
        HttpStatus.FORBIDDEN,
      );
    }
    return project;
  }

  private async requireProject(slug: string, user: AuthenticatedUser) {
    const project = await this.repository.findAccessibleProject(slug, user.id);
    if (!project) {
      throw createProjectError(
        'PROJECT_NOT_FOUND',
        'business',
        'The requested project does not exist or is not accessible.',
        HttpStatus.NOT_FOUND,
      );
    }
    return project;
  }
}
