import { ApiProperty } from '@nestjs/swagger';
import { DOC_TYPES } from '@symphony/shared';
import { IsIn, IsString, MaxLength, MinLength } from 'class-validator';

export class CreateDocumentDto {
  @ApiProperty({ description: 'Document title.' })
  @IsString()
  @MaxLength(120)
  @MinLength(2)
  title!: string;

  @ApiProperty({ description: 'Document type.', enum: DOC_TYPES })
  @IsIn(DOC_TYPES)
  docType!: (typeof DOC_TYPES)[number];
}
