import { ApiProperty } from '@nestjs/swagger';

export class AgentKeyResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty()
  name!: string;

  @ApiProperty()
  keyPrefix!: string;

  @ApiProperty({ type: [String] })
  capabilities!: string[];

  @ApiProperty()
  active!: boolean;

  @ApiProperty({ nullable: true })
  lastUsedAt!: Date | null;
}

export class CreatedAgentKeyResponseDto extends AgentKeyResponseDto {
  @ApiProperty()
  rawKey!: string;
}
