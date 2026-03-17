import { Injectable } from '@nestjs/common';
import type {
  AuthenticatedUser,
  DocumentRecord as SharedDocumentRecord,
} from '@symphony/shared';
import { DOC_TYPES, DOCUMENT_TEMPLATES } from '@symphony/shared';
import type { DocType } from '@prisma/client';
import { EncryptionService } from '../common/security/encryption.service';
import { ProjectAccessService } from '../projects/project-access.service';
import { ProjectsRepository } from '../projects/projects.repository';
import { buildSlug } from '../projects/projects.utils';
import { documentErrors } from './documents.errors';
import { toDocumentRecord } from './documents.mappers';
import { DocumentsRepository } from './documents.repository';
import { ProofClient } from './proof.client';
import type { CreateDocumentDto } from './dto/create-document.dto';
import type { UpdateDocumentDto } from './dto/update-document.dto';

@Injectable()
export class DocumentsService {
  constructor(
    private readonly accessService: ProjectAccessService,
    private readonly documentsRepository: DocumentsRepository,
    private readonly encryptionService: EncryptionService,
    private readonly projectsRepository: ProjectsRepository,
    private readonly proofClient: ProofClient,
  ) {}

  async create(
    projectSlug: string,
    dto: CreateDocumentDto,
    user: AuthenticatedUser,
  ): Promise<SharedDocumentRecord> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureWriteAccess(project, user);
    const slug = buildSlug(dto.title);
    const proofDocument = await this.proofClient.createDocument({
      content: DOCUMENT_TEMPLATES[dto.docType],
      slug: `${project.slug}-${slug}`,
      title: dto.title,
    });
    const document = await this.documentsRepository.createDocument({
      createdById: user.id,
      docType: dto.docType as DocType,
      projectId: project.id,
      proofAccessToken: this.encryptionService.encrypt(proofDocument.accessToken),
      proofDocSlug: proofDocument.slug,
      proofOwnerSecret: this.encryptionService.encrypt(proofDocument.ownerSecret),
      slug,
      title: dto.title,
    });

    return toDocumentRecord(document, this.proofClient);
  }

  async detail(
    projectSlug: string,
    documentSlug: string,
    user: AuthenticatedUser,
  ): Promise<SharedDocumentRecord> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureReadAccess(project, user);
    return this.getDocumentRecord(project.id, documentSlug);
  }

  async list(
    projectSlug: string,
    user: AuthenticatedUser,
  ): Promise<SharedDocumentRecord[]> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureReadAccess(project, user);
    const documents = await this.documentsRepository.listByProject(project.id);
    return documents.map((document) => toDocumentRecord(document, this.proofClient));
  }

  async remove(
    projectSlug: string,
    documentSlug: string,
    user: AuthenticatedUser,
  ): Promise<void> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureWriteAccess(project, user);
    const document = await this.getDocumentEntity(project.id, documentSlug);
    await this.documentsRepository.softDelete(document.id);
  }

  async update(
    projectSlug: string,
    documentSlug: string,
    dto: UpdateDocumentDto,
    user: AuthenticatedUser,
  ): Promise<SharedDocumentRecord> {
    const project = await this.getProject(projectSlug);
    this.accessService.ensureWriteAccess(project, user);
    const document = await this.getDocumentEntity(project.id, documentSlug);
    const updated = await this.documentsRepository.updateDocument(document.id, {
      docType: dto.docType ? (dto.docType as DocType) : document.docType,
      slug: dto.title ? buildSlug(dto.title) : document.slug,
      title: dto.title ?? document.title,
    });

    return toDocumentRecord(updated, this.proofClient);
  }

  private async getDocumentEntity(projectId: string, documentSlug: string) {
    const document = await this.documentsRepository.findByProjectAndSlug(
      projectId,
      documentSlug,
    );

    if (!document) {
      throw documentErrors.documentNotFound(documentSlug);
    }

    return document;
  }

  private async getDocumentRecord(projectId: string, documentSlug: string) {
    return toDocumentRecord(
      await this.getDocumentEntity(projectId, documentSlug),
      this.proofClient,
    );
  }

  private async getProject(projectSlug: string) {
    const project = await this.projectsRepository.findBySlug(projectSlug);

    if (!project) {
      throw documentErrors.documentNotFound(projectSlug);
    }

    return project;
  }
}
