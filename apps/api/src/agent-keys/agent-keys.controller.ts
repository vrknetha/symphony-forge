import { Body, Controller, Delete, Get, Param, Post } from '@nestjs/common';
import {
  ApiCreatedResponse,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from '@nestjs/swagger';
import { Role } from '@prisma/client';
import { Roles } from '../common/decorators/roles.decorator';
import { AgentKeysService } from './agent-keys.service';
import {
  AgentKeyResponseDto,
  CreatedAgentKeyResponseDto,
} from './dto/agent-key-response.dto';
import { CreateAgentKeyDto } from './dto/create-agent-key.dto';

@ApiTags('Agent Keys')
@Controller('agent-keys')
@Roles(Role.ADMIN)
export class AgentKeysController {
  constructor(private readonly service: AgentKeysService) {}

  @Post()
  @ApiCreatedResponse({ type: CreatedAgentKeyResponseDto })
  @ApiOperation({ summary: 'Create an agent API key' })
  create(@Body() dto: CreateAgentKeyDto) {
    return this.service.createAgentKey(dto);
  }

  @Delete(':id')
  @ApiOkResponse({ schema: { example: { success: true } } })
  @ApiOperation({ summary: 'Revoke an agent API key' })
  revoke(@Param('id') id: string) {
    return this.service.revokeAgentKey(id);
  }

  @Get()
  @ApiOkResponse({ type: [AgentKeyResponseDto] })
  @ApiOperation({ summary: 'List agent API keys' })
  list() {
    return this.service.listAgentKeys();
  }
}
