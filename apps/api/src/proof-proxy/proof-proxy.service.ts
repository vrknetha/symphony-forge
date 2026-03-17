import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { AgentKeysService } from '../agent-keys/agent-keys.service';
import { EncryptionService } from '../common/security/encryption.service';
import type { AuthenticatedUser } from '@symphony/shared';
import { ProjectAccessService } from '../projects/project-access.service';
import { ProjectsRepository } from '../projects/projects.repository';
import { documentErrors } from '../documents/documents.errors';
import { DocumentsRepository } from '../documents/documents.repository';

interface ProofProxyAccessInput {
  agentKey?: Awaited<ReturnType<AgentKeysService['authenticate']>>;
  documentSlug: string;
  projectSlug: string;
  user?: AuthenticatedUser;
}

@Injectable()
export class ProofProxyService {
  constructor(
    private readonly accessService: ProjectAccessService,
    private readonly agentKeysService: AgentKeysService,
    private readonly configService: ConfigService,
    private readonly documentsRepository: DocumentsRepository,
    private readonly encryptionService: EncryptionService,
    private readonly projectsRepository: ProjectsRepository,
  ) {}

  async buildEditorUrl(input: ProofProxyAccessInput): Promise<string> {
    const document = await this.documentsRepository.findByRoute(
      input.projectSlug,
      input.documentSlug,
    );

    if (!document) {
      throw documentErrors.documentNotFound(input.documentSlug);
    }

    if (input.user) {
      const project = await this.projectsRepository.findBySlug(input.projectSlug);

      if (!project) {
        throw documentErrors.documentNotFound(input.projectSlug);
      }

      this.accessService.ensureReadAccess(project, input.user);
    }

    if (input.agentKey && !this.agentKeysService.hasCapability(input.agentKey, 'read')) {
      throw documentErrors.proofRequestFailed();
    }

    const accessToken = this.encryptionService.decrypt(document.proofAccessToken);
    const baseUrl = this.configService.getOrThrow<string>('proof.baseUrl', { infer: true });
    const query = new URLSearchParams({ token: accessToken });

    return `${baseUrl}/documents/${document.proofDocSlug}?${query.toString()}`;
  }
}
