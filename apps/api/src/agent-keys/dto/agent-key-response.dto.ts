import { ApiProperty } from '@nestjs/swagger';
import { AGENT_KEY_CAPABILITIES } from '@symphony/shared';

export class AgentKeyResponseDto {
  @ApiProperty({ description: 'Agent key identifier.' })
  id!: string;

  @ApiProperty({ description: 'Friendly key name.' })
  name!: string;

  @ApiProperty({ description: 'Key prefix used for display.' })
  keyPrefix!: string;

  @ApiProperty({
    description: 'Capabilities granted to the key.',
    enum: AGENT_KEY_CAPABILITIES,
    isArray: true,
  })
  capabilities!: (typeof AGENT_KEY_CAPABILITIES)[number][];

  @ApiProperty({ description: 'Whether the key is active.' })
  active!: boolean;

  @ApiProperty({ description: 'Creation timestamp.' })
  createdAt!: string;

  @ApiProperty({ description: 'Timestamp of the last key usage.', nullable: true })
  lastUsedAt!: string | null;
}
