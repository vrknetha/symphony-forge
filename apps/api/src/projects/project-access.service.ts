import { Injectable } from '@nestjs/common';
import type { AuthenticatedUser } from '@symphony/shared';
import type { ProjectRecord } from './projects.repository';
import { projectErrors } from './projects.errors';

@Injectable()
export class ProjectAccessService {
  ensureReadAccess(project: ProjectRecord, user: AuthenticatedUser): void {
    if (user.role === 'ADMIN') {
      return;
    }

    const isOwner = project.ownerId === user.id;
    const isMember = project.members.some((member) => member.userId === user.id);

    if (!isOwner && !isMember) {
      throw projectErrors.userForbidden();
    }
  }

  ensureWriteAccess(project: ProjectRecord, user: AuthenticatedUser): void {
    if (user.role === 'ADMIN' || project.ownerId === user.id) {
      return;
    }

    const member = project.members.find((item) => item.userId === user.id);

    if (!member || member.role === 'VIEWER') {
      throw projectErrors.userForbidden();
    }
  }
}
