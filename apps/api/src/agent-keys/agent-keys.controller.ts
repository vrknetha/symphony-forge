import { Body, Controller, Delete, Get, Param, Post } from '@nestjs/common';
import { ApiCookieAuth, ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import { Roles } from '../common/decorators/roles.decorator';
import { AgentKeysService } from './agent-keys.service';
import { AgentKeyResponseDto } from './dto/agent-key-response.dto';
import { CreateAgentKeyDto } from './dto/create-agent-key.dto';
import { CreatedAgentKeyResponseDto } from './dto/created-agent-key-response.dto';

@ApiTags('Agent Keys')
@ApiCookieAuth()
@Roles('ADMIN')
@Controller('api/v1/agent-keys')
export class AgentKeysController {
  constructor(private readonly agentKeysService: AgentKeysService) {}

  @Get()
  @ApiOperation({ summary: 'List agent keys.' })
  @ApiResponse({ status: 200, type: [AgentKeyResponseDto] })
  list() {
    return this.agentKeysService.list();
  }

  @Post()
  @ApiOperation({ summary: 'Create an agent API key.' })
  @ApiResponse({ status: 201, type: CreatedAgentKeyResponseDto })
  create(@Body() dto: CreateAgentKeyDto) {
    return this.agentKeysService.create(dto);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Revoke an agent API key.' })
  @ApiResponse({ status: 200, type: AgentKeyResponseDto })
  async revoke(@Param('id') id: string): Promise<{ revoked: boolean }> {
    await this.agentKeysService.revoke(id);
    return { revoked: true };
  }
}
