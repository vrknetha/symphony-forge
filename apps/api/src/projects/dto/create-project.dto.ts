import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, MaxLength, MinLength } from 'class-validator';

export class CreateProjectDto {
  @ApiProperty({ example: 'Client Portal Refresh' })
  @IsString()
  @MaxLength(120)
  @MinLength(2)
  name!: string;

  @ApiPropertyOptional({
    example: 'Internal upgrade for the client portal roadmap.',
  })
  @IsOptional()
  @IsString()
  @MaxLength(500)
  description?: string;
}
