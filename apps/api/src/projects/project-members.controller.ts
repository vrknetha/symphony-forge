import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
} from '@nestjs/common';
import {
  ApiCreatedResponse,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from '@nestjs/swagger';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { AuthenticatedUser } from '../common/types/authenticated-user';
import {
  AddProjectMemberDto,
  UpdateProjectMemberDto,
} from './dto/project-member.dto';
import { ProjectMemberResponseDto } from './dto/project-response.dto';
import { ProjectsService } from './projects.service';

@ApiTags('Project Members')
@Controller('projects/:slug/members')
export class ProjectMembersController {
  constructor(private readonly service: ProjectsService) {}

  @Post()
  @ApiCreatedResponse({ type: ProjectMemberResponseDto })
  @ApiOperation({ summary: 'Add a member to a project' })
  addMember(
    @Body() dto: AddProjectMemberDto,
    @CurrentUser() user: AuthenticatedUser,
    @Param('slug') slug: string,
  ) {
    return this.service.addMember(dto, slug, user);
  }

  @Delete(':memberId')
  @ApiOkResponse({ schema: { example: { success: true } } })
  @ApiOperation({ summary: 'Remove a member from a project' })
  removeMember(
    @CurrentUser() user: AuthenticatedUser,
    @Param('memberId') memberId: string,
    @Param('slug') slug: string,
  ) {
    return this.service.removeMember(memberId, slug, user);
  }

  @Get()
  @ApiOkResponse({ type: [ProjectMemberResponseDto] })
  @ApiOperation({ summary: 'List project members' })
  listMembers(
    @CurrentUser() user: AuthenticatedUser,
    @Param('slug') slug: string,
  ) {
    return this.service.listMembers(slug, user);
  }

  @Patch(':memberId')
  @ApiOkResponse({ type: ProjectMemberResponseDto })
  @ApiOperation({ summary: 'Update a project member role' })
  updateMember(
    @Body() dto: UpdateProjectMemberDto,
    @CurrentUser() user: AuthenticatedUser,
    @Param('memberId') memberId: string,
    @Param('slug') slug: string,
  ) {
    return this.service.updateMember(memberId, dto, slug, user);
  }
}
