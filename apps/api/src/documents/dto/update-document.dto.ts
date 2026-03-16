import { ApiPropertyOptional } from '@nestjs/swagger';
import { DocType } from '@prisma/client';
import {
  IsEnum,
  IsOptional,
  IsString,
  MaxLength,
  MinLength,
} from 'class-validator';

export class UpdateDocumentDto {
  @ApiPropertyOptional({ enum: DocType })
  @IsEnum(DocType)
  @IsOptional()
  docType?: DocType;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @MaxLength(160)
  @MinLength(2)
  title?: string;
}
