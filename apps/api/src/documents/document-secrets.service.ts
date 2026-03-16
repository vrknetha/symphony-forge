import { createCipheriv, createHash, randomBytes } from 'crypto';
import { Inject, Injectable } from '@nestjs/common';
import { ConfigType } from '@nestjs/config';
import { environment } from '../config/environment';

@Injectable()
export class DocumentSecretsService {
  constructor(
    @Inject(environment.KEY)
    private readonly env: ConfigType<typeof environment>,
  ) {}

  encrypt(plainText: string): string {
    const iv = randomBytes(12);
    const key = createHash('sha256').update(this.env.appEncryptionKey).digest();
    const cipher = createCipheriv('aes-256-gcm', key, iv);
    const encrypted = Buffer.concat([
      cipher.update(plainText, 'utf8'),
      cipher.final(),
    ]);
    const authTag = cipher.getAuthTag();
    return `${iv.toString('base64')}.${authTag.toString('base64')}.${encrypted.toString('base64')}`;
  }
}
