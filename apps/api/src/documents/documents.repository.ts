import { Injectable } from '@nestjs/common';
import { Prisma, type DocType } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

const documentInclude = {
  createdBy: true,
  project: true,
} satisfies Prisma.DocumentInclude;

export type DocumentRecord = Prisma.DocumentGetPayload<{
  include: typeof documentInclude;
}>;

@Injectable()
export class DocumentsRepository {
  constructor(private readonly prisma: PrismaService) {}

  async createDocument(
    data: Prisma.DocumentUncheckedCreateInput,
  ): Promise<DocumentRecord> {
    return this.prisma.document.create({
      data,
      include: documentInclude,
    });
  }

  async findByProjectAndSlug(
    projectId: string,
    slug: string,
  ): Promise<DocumentRecord | null> {
    return this.prisma.document.findFirst({
      include: documentInclude,
      where: { deletedAt: null, projectId, slug },
    });
  }

  async findByRoute(
    projectSlug: string,
    documentSlug: string,
  ): Promise<DocumentRecord | null> {
    return this.prisma.document.findFirst({
      include: documentInclude,
      where: {
        deletedAt: null,
        project: { slug: projectSlug },
        slug: documentSlug,
      },
    });
  }

  async listByProject(projectId: string): Promise<DocumentRecord[]> {
    return this.prisma.document.findMany({
      include: documentInclude,
      orderBy: { updatedAt: 'desc' },
      where: { deletedAt: null, projectId },
    });
  }

  async softDelete(id: string): Promise<void> {
    await this.prisma.document.update({
      data: { deletedAt: new Date() },
      where: { id },
    });
  }

  async updateDocument(
    id: string,
    data: Prisma.DocumentUncheckedUpdateInput,
  ): Promise<DocumentRecord> {
    return this.prisma.document.update({
      data,
      include: documentInclude,
      where: { id },
    });
  }
}
