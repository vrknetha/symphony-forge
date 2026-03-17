import { ApiProperty } from '@nestjs/swagger';
import { DOC_TYPES } from '@symphony/shared';
import { AuthUserResponseDto } from '../../auth/dto/auth-user-response.dto';

export class DocumentResponseDto {
  @ApiProperty({ description: 'Document identifier.' })
  id!: string;

  @ApiProperty({ description: 'Document slug.' })
  slug!: string;

  @ApiProperty({ description: 'Document title.' })
  title!: string;

  @ApiProperty({ description: 'Document type.', enum: DOC_TYPES })
  docType!: (typeof DOC_TYPES)[number];

  @ApiProperty({ description: 'Project slug.' })
  projectSlug!: string;

  @ApiProperty({ description: 'Authenticated Proof editor URL.' })
  editorUrl!: string;

  @ApiProperty({ description: 'Creation timestamp.' })
  createdAt!: string;

  @ApiProperty({ description: 'Most recent update timestamp.' })
  updatedAt!: string;

  @ApiProperty({ description: 'User who created the document.', type: AuthUserResponseDto })
  createdBy!: AuthUserResponseDto;
}
