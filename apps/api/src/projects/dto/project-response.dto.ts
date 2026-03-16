import { ApiProperty } from '@nestjs/swagger';
import { MemberRole, ProjectStatus, Role } from '@prisma/client';

export class ProjectMemberResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty()
  userId!: string;

  @ApiProperty()
  name!: string;

  @ApiProperty()
  email!: string;

  @ApiProperty({ enum: Role })
  role!: Role;

  @ApiProperty({ enum: MemberRole })
  memberRole!: MemberRole;
}

export class ProjectResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty()
  name!: string;

  @ApiProperty()
  slug!: string;

  @ApiProperty({ nullable: true })
  description!: string | null;

  @ApiProperty({ enum: ProjectStatus })
  status!: ProjectStatus;

  @ApiProperty()
  ownerId!: string;

  @ApiProperty()
  ownerName!: string;

  @ApiProperty()
  documentCount!: number;
}

export class ProjectDetailResponseDto extends ProjectResponseDto {
  @ApiProperty({ type: () => [ProjectMemberResponseDto] })
  members!: ProjectMemberResponseDto[];
}
