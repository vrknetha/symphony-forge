import { Module } from '@nestjs/common';
import { ProjectMembersController } from './project-members.controller';
import { ProjectsController } from './projects.controller';
import { ProjectsRepository } from './projects.repository';
import { ProjectsService } from './projects.service';

@Module({
  controllers: [ProjectsController, ProjectMembersController],
  providers: [ProjectsRepository, ProjectsService],
})
export class ProjectsModule {}
