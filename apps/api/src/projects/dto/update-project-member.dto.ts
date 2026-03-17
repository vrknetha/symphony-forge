import { ApiProperty } from '@nestjs/swagger';
import { MEMBER_ROLES } from '@symphony/shared';
import { IsIn } from 'class-validator';

export class UpdateProjectMemberDto {
  @ApiProperty({ description: 'Updated project role.', enum: MEMBER_ROLES })
  @IsIn(MEMBER_ROLES)
  role!: (typeof MEMBER_ROLES)[number];
}
