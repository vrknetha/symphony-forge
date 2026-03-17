import { createCipheriv, createDecipheriv, createHash, randomBytes } from 'node:crypto';
import { Injectable } from '@nestjs/common';
import { AppException } from '../errors/app-exception';

const ENCRYPTION_ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 12;

@Injectable()
export class EncryptionService {
  decrypt(ciphertext: string): string {
    const [ivHex, tagHex, payloadHex] = ciphertext.split(':');

    if (!ivHex || !tagHex || !payloadHex) {
      throw new AppException({
        category: 'INTERNAL',
        code: 'ENCRYPTION_PAYLOAD_INVALID',
        description: 'The encrypted payload format is invalid.',
        status: 500,
      });
    }

    const decipher = createDecipheriv(
      ENCRYPTION_ALGORITHM,
      this.getKey(),
      Buffer.from(ivHex, 'hex'),
    );

    decipher.setAuthTag(Buffer.from(tagHex, 'hex'));
    return Buffer.concat([
      decipher.update(Buffer.from(payloadHex, 'hex')),
      decipher.final(),
    ]).toString('utf8');
  }

  encrypt(value: string): string {
    const iv = randomBytes(IV_LENGTH);
    const cipher = createCipheriv(ENCRYPTION_ALGORITHM, this.getKey(), iv);
    const encrypted = Buffer.concat([cipher.update(value, 'utf8'), cipher.final()]);
    const tag = cipher.getAuthTag();

    return [iv.toString('hex'), tag.toString('hex'), encrypted.toString('hex')].join(':');
  }

  private getKey(): Buffer {
    const secret = process.env.APP_ENCRYPTION_KEY ?? '';

    if (secret.trim().length < 32) {
      throw new AppException({
        category: 'INTERNAL',
        code: 'APP_ENCRYPTION_KEY_INVALID',
        description: 'APP_ENCRYPTION_KEY must be at least 32 characters long.',
        status: 500,
      });
    }

    return createHash('sha256').update(secret).digest();
  }
}
