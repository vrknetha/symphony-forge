import axios, { AxiosInstance } from 'axios';
import { Inject, Injectable, HttpStatus } from '@nestjs/common';
import { ConfigType } from '@nestjs/config';
import { environment } from '../../config/environment';
import { AppException } from '../../common/errors/app-exception';

interface ProofCreateResult {
  accessToken: string;
  ownerSecret: string;
  slug: string;
}

function readString(
  source: Record<string, unknown>,
  keys: string[],
): string | null {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'string' && value.length > 0) {
      return value;
    }
  }
  return null;
}

@Injectable()
export class ProofClient {
  private readonly client: AxiosInstance;

  constructor(@Inject(environment.KEY) env: ConfigType<typeof environment>) {
    this.client = axios.create({
      baseURL: env.proofBaseUrl,
      headers: {
        Authorization: `Bearer ${env.proofApiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }

  async createDocument(
    slug: string,
    template: string,
    title: string,
  ): Promise<ProofCreateResult> {
    try {
      const response = await this.client.post('/documents', {
        content: template,
        slug,
        title,
      });
      const payload = response.data as Record<string, unknown>;
      const proofSlug = readString(payload, [
        'slug',
        'docSlug',
        'proofDocSlug',
      ]);
      const ownerSecret = readString(payload, [
        'ownerSecret',
        'proofOwnerSecret',
      ]);
      const accessToken = readString(payload, [
        'accessToken',
        'proofAccessToken',
      ]);
      if (!proofSlug || !ownerSecret || !accessToken) {
        throw new Error('Proof SDK response missing required fields');
      }
      return { accessToken, ownerSecret, slug: proofSlug };
    } catch (error) {
      throw new AppException({
        category: 'external',
        code: 'PROOF_CREATE_FAILED',
        description: 'Proof SDK document creation failed.',
        details: { cause: error instanceof Error ? error.message : 'unknown' },
        message: 'Failed to create document in Proof SDK',
        retryable: true,
        status: HttpStatus.BAD_GATEWAY,
      });
    }
  }
}
