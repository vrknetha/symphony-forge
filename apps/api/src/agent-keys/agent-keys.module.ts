import { Module } from '@nestjs/common';
import { AgentKeysController } from './agent-keys.controller';
import { AgentKeysRepository } from './agent-keys.repository';
import { AgentKeysService } from './agent-keys.service';

@Module({
  controllers: [AgentKeysController],
  exports: [AgentKeysService],
  providers: [AgentKeysRepository, AgentKeysService],
})
export class AgentKeysModule {}
