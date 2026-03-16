import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  Query,
} from '@nestjs/common';
import {
  ApiCreatedResponse,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from '@nestjs/swagger';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { AuthenticatedUser } from '../common/types/authenticated-user';
import { CreateProjectDto } from './dto/create-project.dto';
import { ListProjectsQueryDto } from './dto/list-projects-query.dto';
import {
  ProjectDetailResponseDto,
  ProjectResponseDto,
} from './dto/project-response.dto';
import { UpdateProjectDto } from './dto/update-project.dto';
import { ProjectsService } from './projects.service';

@ApiTags('Projects')
@Controller('projects')
export class ProjectsController {
  constructor(private readonly service: ProjectsService) {}

  @Post()
  @ApiCreatedResponse({ type: ProjectResponseDto })
  @ApiOperation({ summary: 'Create a project' })
  create(
    @Body() dto: CreateProjectDto,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.service.createProject(dto, user);
  }

  @Delete(':slug')
  @ApiOkResponse({ schema: { example: { success: true } } })
  @ApiOperation({ summary: 'Archive a project' })
  archive(@CurrentUser() user: AuthenticatedUser, @Param('slug') slug: string) {
    return this.service.archiveProject(slug, user);
  }

  @Get()
  @ApiOkResponse({ type: [ProjectResponseDto] })
  @ApiOperation({ summary: 'List projects for the current user' })
  list(
    @CurrentUser() user: AuthenticatedUser,
    @Query() query: ListProjectsQueryDto,
  ) {
    return this.service.listProjects(query, user);
  }

  @Get(':slug')
  @ApiOkResponse({ type: ProjectDetailResponseDto })
  @ApiOperation({ summary: 'Get project details' })
  getProject(
    @CurrentUser() user: AuthenticatedUser,
    @Param('slug') slug: string,
  ) {
    return this.service.getProject(slug, user);
  }

  @Patch(':slug')
  @ApiOkResponse({ type: ProjectResponseDto })
  @ApiOperation({ summary: 'Update a project' })
  update(
    @Body() dto: UpdateProjectDto,
    @CurrentUser() user: AuthenticatedUser,
    @Param('slug') slug: string,
  ) {
    return this.service.updateProject(dto, slug, user);
  }
}
