import { Module } from '@nestjs/common';
import { AgentKeysModule } from '../agent-keys/agent-keys.module';
import { AuthModule } from '../auth/auth.module';
import { DocumentsModule } from '../documents/documents.module';
import { ProjectsModule } from '../projects/projects.module';
import { ProofProxyController } from './proof-proxy.controller';
import { ProofProxyGuard } from './proof-proxy.guard';
import { ProofProxyService } from './proof-proxy.service';

@Module({
  controllers: [ProofProxyController],
  imports: [AgentKeysModule, AuthModule, DocumentsModule, ProjectsModule],
  providers: [ProofProxyGuard, ProofProxyService],
})
export class ProofProxyModule {}
