import { ApiProperty } from '@nestjs/swagger';
import { MEMBER_ROLES } from '@symphony/shared';
import { AuthUserResponseDto } from '../../auth/dto/auth-user-response.dto';

export class ProjectMemberResponseDto {
  @ApiProperty({ description: 'Project member identifier.' })
  id!: string;

  @ApiProperty({ description: 'Timestamp when the user joined the project.' })
  joinedAt!: string;

  @ApiProperty({ description: 'Assigned project role.', enum: MEMBER_ROLES })
  role!: (typeof MEMBER_ROLES)[number];

  @ApiProperty({ description: 'User details for the project member.', type: AuthUserResponseDto })
  user!: AuthUserResponseDto;
}
