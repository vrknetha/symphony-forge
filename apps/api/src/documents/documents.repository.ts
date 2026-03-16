import { DocType } from '@prisma/client';
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

interface DocumentFilters {
  docType?: DocType;
  search?: string;
}

@Injectable()
export class DocumentsRepository {
  constructor(private readonly prisma: PrismaService) {}

  createDocument(data: {
    createdById: string;
    docType: DocType;
    projectId: string;
    proofAccessToken: string;
    proofDocSlug: string;
    proofOwnerSecret: string;
    slug: string;
    title: string;
  }) {
    return this.prisma.document.create({
      data,
      include: { createdBy: true, project: true },
    });
  }

  findAccessibleDocument(docSlug: string, projectSlug: string, userId: string) {
    return this.prisma.document.findFirst({
      include: { createdBy: true, project: true },
      where: {
        deletedAt: null,
        project: {
          deletedAt: null,
          slug: projectSlug,
          OR: [{ ownerId: userId }, { members: { some: { userId } } }],
        },
        slug: docSlug,
      },
    });
  }

  findAccessibleProject(projectSlug: string, userId: string) {
    return this.prisma.project.findFirst({
      where: {
        deletedAt: null,
        slug: projectSlug,
        OR: [{ ownerId: userId }, { members: { some: { userId } } }],
      },
    });
  }

  listDocuments(filters: DocumentFilters, projectSlug: string, userId: string) {
    return this.prisma.document.findMany({
      include: { createdBy: true, project: true },
      orderBy: { updatedAt: 'desc' },
      where: {
        deletedAt: null,
        docType: filters.docType,
        project: {
          deletedAt: null,
          slug: projectSlug,
          OR: [{ ownerId: userId }, { members: { some: { userId } } }],
        },
        title: filters.search
          ? { contains: filters.search, mode: 'insensitive' }
          : undefined,
      },
    });
  }

  markDeleted(id: string) {
    return this.prisma.document.update({
      data: { deletedAt: new Date() },
      where: { id },
    });
  }

  updateDocument(
    id: string,
    data: { docType?: DocType; slug?: string; title?: string },
  ) {
    return this.prisma.document.update({
      data,
      include: { createdBy: true, project: true },
      where: { id },
    });
  }
}
