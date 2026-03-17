import { ApiProperty } from '@nestjs/swagger';
import { IsOptional, IsString, MaxLength, MinLength } from 'class-validator';

export class CreateProjectDto {
  @ApiProperty({ description: 'Project name.', example: 'KnackLabs Forge' })
  @IsString()
  @MaxLength(100)
  @MinLength(2)
  name!: string;

  @ApiProperty({
    description: 'Optional project description.',
    example: 'Collaborative workspace for platform planning.',
    required: false,
  })
  @IsOptional()
  @IsString()
  @MaxLength(280)
  description?: string;
}
