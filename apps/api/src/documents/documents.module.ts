import { Module } from '@nestjs/common';
import { DocumentSecretsService } from './document-secrets.service';
import { DocumentsController } from './documents.controller';
import { DocumentsRepository } from './documents.repository';
import { DocumentsService } from './documents.service';
import { ProofClient } from './providers/proof.client';

@Module({
  controllers: [DocumentsController],
  providers: [
    DocumentSecretsService,
    DocumentsRepository,
    DocumentsService,
    ProofClient,
  ],
})
export class DocumentsModule {}
