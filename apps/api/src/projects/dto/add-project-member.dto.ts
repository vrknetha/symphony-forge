import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { MEMBER_ROLES } from '@symphony/shared';
import { IsEmail, IsIn, IsOptional, IsString, MaxLength } from 'class-validator';

export class AddProjectMemberDto {
  @ApiPropertyOptional({ description: 'Existing user email address.' })
  @IsOptional()
  @IsEmail()
  @MaxLength(255)
  email?: string;

  @ApiPropertyOptional({ description: 'Existing Azure AD object ID.' })
  @IsOptional()
  @IsString()
  @MaxLength(100)
  azureOid?: string;

  @ApiProperty({ description: 'Project role for the member.', enum: MEMBER_ROLES })
  @IsIn(MEMBER_ROLES)
  role!: (typeof MEMBER_ROLES)[number];
}
