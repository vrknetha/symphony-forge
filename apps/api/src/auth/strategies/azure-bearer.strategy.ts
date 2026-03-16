import { Injectable, Inject } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ConfigType } from '@nestjs/config';
import {
  BearerStrategy,
  IBearerStrategyOption,
  ITokenPayload,
} from 'passport-azure-ad';
import { environment } from '../../config/environment';
import { AuthService } from '../auth.service';

function metadataUrl(tenantId: string): string {
  return `https://login.microsoftonline.com/${tenantId}/v2.0/.well-known/openid-configuration`;
}

@Injectable()
export class AzureBearerStrategy extends PassportStrategy(
  BearerStrategy,
  'azure-ad',
) {
  constructor(
    private readonly authService: AuthService,
    @Inject(environment.KEY)
    env: ConfigType<typeof environment>,
  ) {
    const options: IBearerStrategyOption = {
      audience: env.azureClientId,
      clientID: env.azureClientId,
      identityMetadata: metadataUrl(env.azureTenantId),
      loggingLevel: 'warn',
      loggingNoPII: true,
      validateIssuer: true,
    };
    super(options);
  }

  validate(token: ITokenPayload) {
    return this.authService.syncAzureUser(token);
  }
}
