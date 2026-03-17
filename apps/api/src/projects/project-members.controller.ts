import { Body, Controller, Delete, Get, Param, Patch, Post } from '@nestjs/common';
import { ApiCookieAuth, ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import type { AuthenticatedUser } from '@symphony/shared';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { AddProjectMemberDto } from './dto/add-project-member.dto';
import { ProjectMemberResponseDto } from './dto/project-member-response.dto';
import { ProjectMembersService } from './project-members.service';
import { UpdateProjectMemberDto } from './dto/update-project-member.dto';

@ApiTags('Project Members')
@ApiCookieAuth()
@Controller('api/v1/projects/:slug/members')
export class ProjectMembersController {
  constructor(private readonly projectMembersService: ProjectMembersService) {}

  @Get()
  @ApiOperation({ summary: 'List members for a project.' })
  @ApiResponse({ status: 200, type: [ProjectMemberResponseDto] })
  async list(@Param('slug') slug: string, @CurrentUser() user: AuthenticatedUser) {
    const project = await this.projectMembersService.listMembers(slug, user);
    return project.members;
  }

  @Post()
  @ApiOperation({ summary: 'Add or update a project member.' })
  @ApiResponse({ status: 201, type: [ProjectMemberResponseDto] })
  create(
    @Param('slug') slug: string,
    @Body() dto: AddProjectMemberDto,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.projectMembersService.addMember(slug, dto, user);
  }

  @Patch(':memberId')
  @ApiOperation({ summary: 'Update a project member role.' })
  @ApiResponse({ status: 200, type: [ProjectMemberResponseDto] })
  update(
    @Param('slug') slug: string,
    @Param('memberId') memberId: string,
    @Body() dto: UpdateProjectMemberDto,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.projectMembersService.updateMember(slug, memberId, dto, user);
  }

  @Delete(':memberId')
  @ApiOperation({ summary: 'Remove a project member.' })
  @ApiResponse({ status: 200, type: [ProjectMemberResponseDto] })
  remove(
    @Param('slug') slug: string,
    @Param('memberId') memberId: string,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.projectMembersService.removeMember(slug, memberId, user);
  }
}
