import axios from 'axios';
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { getCorrelationId } from '../common/correlation/correlation.storage';
import { documentErrors } from './documents.errors';

interface CreateProofDocumentInput {
  content: string;
  slug: string;
  title: string;
}

interface CreateProofDocumentResponse {
  accessToken: string;
  ownerSecret: string;
  slug: string;
}

@Injectable()
export class ProofClient {
  constructor(private readonly configService: ConfigService) {}

  async createDocument(
    input: CreateProofDocumentInput,
  ): Promise<CreateProofDocumentResponse> {
    try {
      const response = await axios.post<CreateProofDocumentResponse>(
        `${this.getBaseUrl()}/documents`,
        input,
        {
          headers: {
            'x-api-key': this.configService.getOrThrow<string>('proof.apiKey', {
              infer: true,
            }),
            'x-correlation-id': getCorrelationId(),
          },
          timeout: this.configService.getOrThrow<number>('proof.timeoutMs', {
            infer: true,
          }),
        },
      );

      return response.data;
    } catch {
      throw documentErrors.proofRequestFailed();
    }
  }

  buildEditorUrl(projectSlug: string, documentSlug: string): string {
    return `/documents/${projectSlug}/${documentSlug}`;
  }

  private getBaseUrl(): string {
    return this.configService.getOrThrow<string>('proof.baseUrl', { infer: true });
  }
}
