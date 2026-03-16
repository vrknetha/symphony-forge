import { ApiPropertyOptional } from '@nestjs/swagger';
import { DocType } from '@prisma/client';
import { IsEnum, IsOptional, IsString, MaxLength } from 'class-validator';

export class ListDocumentsQueryDto {
  @ApiPropertyOptional({ enum: DocType })
  @IsEnum(DocType)
  @IsOptional()
  docType?: DocType;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @MaxLength(160)
  search?: string;
}
