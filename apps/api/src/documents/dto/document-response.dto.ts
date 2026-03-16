import { ApiProperty } from '@nestjs/swagger';
import { DocType } from '@prisma/client';

export class DocumentResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty()
  title!: string;

  @ApiProperty()
  slug!: string;

  @ApiProperty({ enum: DocType })
  docType!: DocType;

  @ApiProperty()
  projectId!: string;

  @ApiProperty()
  projectSlug!: string;

  @ApiProperty()
  createdById!: string;

  @ApiProperty()
  createdByName!: string;

  @ApiProperty()
  proofDocSlug!: string;

  @ApiProperty()
  proofAccessToken!: string;
}
