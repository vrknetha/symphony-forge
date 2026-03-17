import { ApiProperty } from '@nestjs/swagger';
import { AGENT_KEY_CAPABILITIES } from '@symphony/shared';
import { ArrayMinSize, IsArray, IsIn, IsString, MaxLength, MinLength } from 'class-validator';

export class CreateAgentKeyDto {
  @ApiProperty({ description: 'Friendly name for the key.' })
  @IsString()
  @MaxLength(100)
  @MinLength(2)
  name!: string;

  @ApiProperty({ description: 'Capabilities granted to the key.', enum: AGENT_KEY_CAPABILITIES, isArray: true })
  @ArrayMinSize(1)
  @IsArray()
  @IsIn(AGENT_KEY_CAPABILITIES, { each: true })
  capabilities!: (typeof AGENT_KEY_CAPABILITIES)[number][];
}
