import { ApiProperty } from '@nestjs/swagger';
import { ArrayMaxSize, IsArray, IsString, MaxLength } from 'class-validator';

export class CreateAgentKeyDto {
  @ApiProperty({ example: 'codex-worker' })
  @IsString()
  @MaxLength(120)
  name!: string;

  @ApiProperty({ type: [String], example: ['read', 'comment', 'edit'] })
  @ArrayMaxSize(10)
  @IsArray()
  @IsString({ each: true })
  @MaxLength(50, { each: true })
  capabilities!: string[];
}
