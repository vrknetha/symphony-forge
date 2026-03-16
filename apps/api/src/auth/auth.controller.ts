import {
  Controller,
  Get,
  HttpCode,
  Post,
  Req,
  Res,
  UseGuards,
} from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Response } from 'express';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Public } from '../common/decorators/public.decorator';
import { AuthenticatedUser } from '../common/types/authenticated-user';
import { ACCESS_TOKEN_COOKIE } from './auth.constants';
import { MeResponseDto } from './dto/me-response.dto';
import { AzureOidcGuard } from './guards/azure-oidc.guard';

interface OidcRequest {
  user?: {
    accessToken: string;
    user: AuthenticatedUser;
  };
}

@ApiTags('Auth')
@Controller('auth')
export class AuthController {
  @Get('callback')
  @Public()
  @UseGuards(AzureOidcGuard)
  @ApiOperation({
    summary: 'Handle Azure AD callback and set the access token cookie',
  })
  callback(@Req() request: OidcRequest, @Res() response: Response) {
    if (request.user) {
      response.cookie(ACCESS_TOKEN_COOKIE, request.user.accessToken, {
        httpOnly: true,
        sameSite: 'lax',
      });
    }
    response.redirect('/projects');
  }

  @Get('login')
  @Public()
  @UseGuards(AzureOidcGuard)
  @ApiOperation({ summary: 'Start the Azure AD login redirect flow' })
  login() {
    return undefined;
  }

  @Get('me')
  @ApiOperation({ summary: 'Return the current authenticated user' })
  @ApiOkResponse({ type: MeResponseDto })
  me(@CurrentUser() user: AuthenticatedUser): MeResponseDto {
    return {
      azureOid: user.azureOid,
      email: user.email,
      id: user.id,
      name: user.name,
      role: user.role,
    };
  }

  @Post('logout')
  @HttpCode(200)
  @ApiOperation({ summary: 'Clear the local access token cookie' })
  logout(@Res({ passthrough: true }) response: Response) {
    response.clearCookie(ACCESS_TOKEN_COOKIE);
    return { success: true };
  }
}
