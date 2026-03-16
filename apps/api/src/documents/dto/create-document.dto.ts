import { ApiProperty } from '@nestjs/swagger';
import { DocType } from '@prisma/client';
import { IsEnum, IsString, MaxLength, MinLength } from 'class-validator';

export class CreateDocumentDto {
  @ApiProperty({ enum: DocType })
  @IsEnum(DocType)
  docType!: DocType;

  @ApiProperty({ example: 'Phase 1 rollout plan' })
  @IsString()
  @MaxLength(160)
  @MinLength(2)
  title!: string;
}
