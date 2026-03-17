import { ApiProperty } from '@nestjs/swagger';
import { PROJECT_STATUSES } from '@symphony/shared';
import { AuthUserResponseDto } from '../../auth/dto/auth-user-response.dto';
import { ProjectMemberResponseDto } from './project-member-response.dto';

export class ProjectResponseDto {
  @ApiProperty({ description: 'Project identifier.' })
  id!: string;

  @ApiProperty({ description: 'Human-friendly project name.' })
  name!: string;

  @ApiProperty({ description: 'Project slug.' })
  slug!: string;

  @ApiProperty({ description: 'Optional project description.', nullable: true })
  description!: string | null;

  @ApiProperty({ description: 'Project lifecycle status.', enum: PROJECT_STATUSES })
  status!: (typeof PROJECT_STATUSES)[number];

  @ApiProperty({ description: 'Project owner.', type: AuthUserResponseDto })
  owner!: AuthUserResponseDto;

  @ApiProperty({ description: 'Project members.', type: [ProjectMemberResponseDto] })
  members!: ProjectMemberResponseDto[];

  @ApiProperty({ description: 'Number of active documents in the project.' })
  documentCount!: number;

  @ApiProperty({ description: 'Most recent project update timestamp.' })
  updatedAt!: string;
}
