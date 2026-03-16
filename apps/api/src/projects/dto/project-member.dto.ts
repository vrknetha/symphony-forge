import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { MemberRole } from '@prisma/client';
import {
  IsEmail,
  IsEnum,
  IsOptional,
  IsString,
  MaxLength,
} from 'class-validator';

export class AddProjectMemberDto {
  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  azureOid?: string;

  @ApiPropertyOptional()
  @IsEmail()
  @IsOptional()
  @MaxLength(255)
  email?: string;

  @ApiProperty({ enum: MemberRole })
  @IsEnum(MemberRole)
  role!: MemberRole;
}

export class UpdateProjectMemberDto {
  @ApiProperty({ enum: MemberRole })
  @IsEnum(MemberRole)
  role!: MemberRole;
}
