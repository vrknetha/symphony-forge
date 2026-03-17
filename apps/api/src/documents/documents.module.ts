import { Module } from '@nestjs/common';
import { ProjectsModule } from '../projects/projects.module';
import { DocumentsController } from './documents.controller';
import { DocumentsRepository } from './documents.repository';
import { DocumentsService } from './documents.service';
import { ProofClient } from './proof.client';

@Module({
  controllers: [DocumentsController],
  imports: [ProjectsModule],
  exports: [DocumentsRepository, ProofClient],
  providers: [DocumentsRepository, DocumentsService, ProofClient],
})
export class DocumentsModule {}
