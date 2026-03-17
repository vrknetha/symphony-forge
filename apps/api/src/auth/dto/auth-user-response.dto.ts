import { ApiProperty } from '@nestjs/swagger';
import { USER_ROLES, type AuthenticatedUser } from '@symphony/shared';

export class AuthUserResponseDto implements AuthenticatedUser {
  @ApiProperty({ description: 'Internal user identifier.' })
  id!: string;

  @ApiProperty({ description: 'Azure AD object identifier.' })
  azureOid!: string;

  @ApiProperty({ description: 'User email address.' })
  email!: string;

  @ApiProperty({ description: 'Display name for the authenticated user.' })
  name!: string;

  @ApiProperty({ description: 'Forge role for the user.', enum: USER_ROLES })
  role!: (typeof USER_ROLES)[number];
}
