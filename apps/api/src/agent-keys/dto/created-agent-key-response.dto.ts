import { ApiProperty } from '@nestjs/swagger';
import { AgentKeyResponseDto } from './agent-key-response.dto';

export class CreatedAgentKeyResponseDto extends AgentKeyResponseDto {
  @ApiProperty({ description: 'Raw agent key shown only once.' })
  rawKey!: string;
}
