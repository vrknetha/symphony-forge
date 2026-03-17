import { Controller, Delete, Get, Param, Patch, Post, Body } from '@nestjs/common';
import { ApiCookieAuth, ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import type { AuthenticatedUser } from '@symphony/shared';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { CreateProjectDto } from './dto/create-project.dto';
import { ProjectResponseDto } from './dto/project-response.dto';
import { UpdateProjectDto } from './dto/update-project.dto';
import { ProjectsService } from './projects.service';

@ApiTags('Projects')
@ApiCookieAuth()
@Controller('api/v1/projects')
export class ProjectsController {
  constructor(private readonly projectsService: ProjectsService) {}

  @Get()
  @ApiOperation({ summary: 'List projects for the current user.' })
  @ApiResponse({ status: 200, type: [ProjectResponseDto] })
  list(@CurrentUser() user: AuthenticatedUser) {
    return this.projectsService.list(user);
  }

  @Post()
  @ApiOperation({ summary: 'Create a project.' })
  @ApiResponse({ status: 201, type: ProjectResponseDto })
  create(@Body() dto: CreateProjectDto, @CurrentUser() user: AuthenticatedUser) {
    return this.projectsService.create(dto, user);
  }

  @Get(':slug')
  @ApiOperation({ summary: 'Fetch project details by slug.' })
  @ApiResponse({ status: 200, type: ProjectResponseDto })
  detail(@Param('slug') slug: string, @CurrentUser() user: AuthenticatedUser) {
    return this.projectsService.getBySlug(slug, user);
  }

  @Patch(':slug')
  @ApiOperation({ summary: 'Update a project.' })
  @ApiResponse({ status: 200, type: ProjectResponseDto })
  update(
    @Param('slug') slug: string,
    @Body() dto: UpdateProjectDto,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.projectsService.update(slug, dto, user);
  }

  @Delete(':slug')
  @ApiOperation({ summary: 'Archive a project.' })
  @ApiResponse({ status: 200, type: ProjectResponseDto })
  async archive(
    @Param('slug') slug: string,
    @CurrentUser() user: AuthenticatedUser,
  ): Promise<{ archived: boolean }> {
    await this.projectsService.archive(slug, user);
    return { archived: true };
  }
}
