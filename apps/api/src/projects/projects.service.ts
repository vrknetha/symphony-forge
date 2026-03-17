import { ConflictException, Injectable } from '@nestjs/common';
import type { AuthenticatedUser, ProjectRecord as SharedProjectRecord } from '@symphony/shared';
import { ProjectStatus } from '@prisma/client';
import { ProjectAccessService } from './project-access.service';
import { projectErrors } from './projects.errors';
import { toProjectRecord } from './projects.mappers';
import { ProjectsRepository } from './projects.repository';
import { buildSlug } from './projects.utils';
import type { CreateProjectDto } from './dto/create-project.dto';
import type { UpdateProjectDto } from './dto/update-project.dto';

@Injectable()
export class ProjectsService {
  constructor(
    private readonly accessService: ProjectAccessService,
    private readonly repository: ProjectsRepository,
  ) {}

  async archive(slug: string, user: AuthenticatedUser): Promise<void> {
    const project = await this.getProjectEntity(slug);
    this.accessService.ensureWriteAccess(project, user);
    await this.repository.archiveProject(project.id);
  }

  async create(
    dto: CreateProjectDto,
    user: AuthenticatedUser,
  ): Promise<SharedProjectRecord> {
    const slug = buildSlug(dto.name);

    try {
      const project = await this.repository.createProject({
        description: dto.description ?? null,
        name: dto.name,
        ownerId: user.id,
        slug,
        status: ProjectStatus.ACTIVE,
      });

      await this.repository.addMember(project.id, user.id, 'OWNER');
      const created = await this.getProjectEntity(slug);
      return toProjectRecord(created);
    } catch (error: unknown) {
      if (error instanceof ConflictException || isUniqueConstraint(error)) {
        throw projectErrors.slugConflict(slug);
      }

      throw error;
    }
  }

  async getBySlug(slug: string, user: AuthenticatedUser): Promise<SharedProjectRecord> {
    const project = await this.getProjectEntity(slug);
    this.accessService.ensureReadAccess(project, user);
    return toProjectRecord(project);
  }

  async list(user: AuthenticatedUser): Promise<SharedProjectRecord[]> {
    const projects = await this.repository.findProjectsForUser(
      user.id,
      user.role === 'ADMIN',
    );
    return projects.map((project) => toProjectRecord(project));
  }

  async update(
    slug: string,
    dto: UpdateProjectDto,
    user: AuthenticatedUser,
  ): Promise<SharedProjectRecord> {
    const project = await this.getProjectEntity(slug);
    this.accessService.ensureWriteAccess(project, user);

    const updated = await this.repository.updateProject(project.id, {
      description: dto.description ?? project.description,
      name: dto.name ?? project.name,
      slug: dto.name ? buildSlug(dto.name) : project.slug,
    });

    return toProjectRecord(updated);
  }

  private async getProjectEntity(slug: string) {
    const project = await this.repository.findBySlug(slug);

    if (!project) {
      throw projectErrors.projectNotFound(slug);
    }

    return project;
  }
}

function isUniqueConstraint(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    error.code === 'P2002'
  );
}
