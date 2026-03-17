import { Module } from '@nestjs/common';
import { ProjectAccessService } from './project-access.service';
import { ProjectMembersController } from './project-members.controller';
import { ProjectMembersService } from './project-members.service';
import { ProjectsController } from './projects.controller';
import { ProjectsRepository } from './projects.repository';
import { ProjectsService } from './projects.service';

@Module({
  controllers: [ProjectsController, ProjectMembersController],
  exports: [ProjectAccessService, ProjectsRepository],
  providers: [
    ProjectAccessService,
    ProjectMembersService,
    ProjectsRepository,
    ProjectsService,
  ],
})
export class ProjectsModule {}
