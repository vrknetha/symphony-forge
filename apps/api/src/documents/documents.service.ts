import { HttpStatus, Injectable } from '@nestjs/common';
import { DocType } from '@prisma/client';
import { AppException } from '../common/errors/app-exception';
import { AuthenticatedUser } from '../common/types/authenticated-user';
import { toSlug } from '../common/utils/slug';
import { CreateDocumentDto } from './dto/create-document.dto';
import { DocumentResponseDto } from './dto/document-response.dto';
import { ListDocumentsQueryDto } from './dto/list-documents-query.dto';
import { UpdateDocumentDto } from './dto/update-document.dto';
import { DOCUMENT_TEMPLATES } from './document-templates';
import { DocumentsRepository } from './documents.repository';
import { DocumentSecretsService } from './document-secrets.service';
import { ProofClient } from './providers/proof.client';

@Injectable()
export class DocumentsService {
  constructor(
    private readonly repository: DocumentsRepository,
    private readonly proofClient: ProofClient,
    private readonly secrets: DocumentSecretsService,
  ) {}

  async createDocument(
    dto: CreateDocumentDto,
    projectSlug: string,
    user: AuthenticatedUser,
  ): Promise<DocumentResponseDto> {
    const project = await this.requireProject(projectSlug, user);
    const slug = toSlug(dto.title);
    const proof = await this.proofClient.createDocument(
      slug,
      DOCUMENT_TEMPLATES[dto.docType],
      dto.title,
    );
    const document = await this.repository.createDocument({
      createdById: user.id,
      docType: dto.docType,
      projectId: project.id,
      proofAccessToken: proof.accessToken,
      proofDocSlug: proof.slug,
      proofOwnerSecret: this.secrets.encrypt(proof.ownerSecret),
      slug,
      title: dto.title,
    });
    return this.toDocument(document);
  }

  async deleteDocument(
    docSlug: string,
    projectSlug: string,
    user: AuthenticatedUser,
  ) {
    const document = await this.requireDocument(docSlug, projectSlug, user);
    await this.repository.markDeleted(document.id);
    return { success: true };
  }

  async getDocument(
    docSlug: string,
    projectSlug: string,
    user: AuthenticatedUser,
  ): Promise<DocumentResponseDto> {
    return this.toDocument(
      await this.requireDocument(docSlug, projectSlug, user),
    );
  }

  async listDocuments(
    projectSlug: string,
    query: ListDocumentsQueryDto,
    user: AuthenticatedUser,
  ) {
    const documents = await this.repository.listDocuments(
      query,
      projectSlug,
      user.id,
    );
    return documents.map((document) => this.toDocument(document));
  }

  async updateDocument(
    docSlug: string,
    dto: UpdateDocumentDto,
    projectSlug: string,
    user: AuthenticatedUser,
  ): Promise<DocumentResponseDto> {
    const document = await this.requireDocument(docSlug, projectSlug, user);
    const updated = await this.repository.updateDocument(document.id, {
      docType: dto.docType,
      slug: dto.title ? toSlug(dto.title) : undefined,
      title: dto.title,
    });
    return this.toDocument(updated);
  }

  private error(code: string, description: string, status: HttpStatus) {
    return new AppException({
      category: 'business',
      code,
      description,
      message: description,
      retryable: false,
      status,
    });
  }

  private async requireDocument(
    docSlug: string,
    projectSlug: string,
    user: AuthenticatedUser,
  ) {
    const document = await this.repository.findAccessibleDocument(
      docSlug,
      projectSlug,
      user.id,
    );
    if (!document) {
      throw this.error(
        'DOCUMENT_NOT_FOUND',
        'The requested document does not exist or is not accessible.',
        HttpStatus.NOT_FOUND,
      );
    }
    return document;
  }

  private async requireProject(projectSlug: string, user: AuthenticatedUser) {
    const project = await this.repository.findAccessibleProject(
      projectSlug,
      user.id,
    );
    if (!project) {
      throw this.error(
        'PROJECT_NOT_FOUND',
        'The requested project does not exist or is not accessible.',
        HttpStatus.NOT_FOUND,
      );
    }
    return project;
  }

  private toDocument(document: {
    createdBy: { id: string; name: string };
    docType: DocType;
    id: string;
    project: { id: string; slug: string };
    proofAccessToken: string;
    proofDocSlug: string;
    slug: string;
    title: string;
  }): DocumentResponseDto {
    return {
      createdById: document.createdBy.id,
      createdByName: document.createdBy.name,
      docType: document.docType,
      id: document.id,
      projectId: document.project.id,
      projectSlug: document.project.slug,
      proofAccessToken: document.proofAccessToken,
      proofDocSlug: document.proofDocSlug,
      slug: document.slug,
      title: document.title,
    };
  }
}
