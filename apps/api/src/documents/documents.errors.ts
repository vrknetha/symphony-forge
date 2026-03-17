import { HttpStatus } from '@nestjs/common';
import { AppException } from '../common/errors/app-exception';

export const documentErrors = {
  documentNotFound: (slug: string) =>
    new AppException({
      category: 'NOT_FOUND',
      code: 'DOCUMENT_NOT_FOUND',
      description: `Document '${slug}' was not found.`,
      status: HttpStatus.NOT_FOUND,
    }),
  proofRequestFailed: () =>
    new AppException({
      category: 'INTERNAL',
      code: 'PROOF_REQUEST_FAILED',
      description: 'The Proof SDK service could not complete the request.',
      retryable: true,
      status: HttpStatus.BAD_GATEWAY,
    }),
};
