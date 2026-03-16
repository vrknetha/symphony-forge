import { Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class AzureOidcGuard extends AuthGuard('azure-oidc') {}
