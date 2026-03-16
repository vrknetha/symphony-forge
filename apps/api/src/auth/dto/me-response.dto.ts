import { ApiProperty } from '@nestjs/swagger';
import { Role } from '@prisma/client';

export class MeResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty({ nullable: true })
  azureOid!: string | null;

  @ApiProperty()
  email!: string;

  @ApiProperty()
  name!: string;

  @ApiProperty({ enum: Role })
  role!: Role;
}
