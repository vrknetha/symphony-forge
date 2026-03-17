import { Throttle } from '@nestjs/throttler';
import {
  Controller,
  Get,
  HttpCode,
  HttpStatus,
  Post,
  Query,
  Res,
} from '@nestjs/common';
import {
  ApiCookieAuth,
  ApiOperation,
  ApiResponse,
  ApiTags,
} from '@nestjs/swagger';
import type { Response } from 'express';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { Public } from '../common/decorators/public.decorator';
import type { AuthenticatedUser } from '@symphony/shared';
import { AuthUserResponseDto } from './dto/auth-user-response.dto';
import { LoginResponseDto } from './dto/login-response.dto';
import { AuthService } from './auth.service';

const AUTH_RATE_LIMIT = { default: { limit: 10, ttl: 60_000 } };
const AUTH_COOKIE_NAME = 'symphony_forge_session';

@ApiTags('Auth')
@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Get('login')
  @Public()
  @Throttle(AUTH_RATE_LIMIT)
  @ApiOperation({ summary: 'Build the Azure AD login redirect URL.' })
  @ApiResponse({ status: 200, type: LoginResponseDto })
  login(): LoginResponseDto {
    return { url: this.authService.getLoginUrl() };
  }

  @Get('callback')
  @Public()
  @Throttle(AUTH_RATE_LIMIT)
  @ApiOperation({ summary: 'Handle the Azure AD callback and set the session cookie.' })
  @ApiResponse({ status: 200, type: LoginResponseDto })
  async callback(
    @Query('code') code: string | undefined,
    @Res({ passthrough: true }) response: Response,
  ): Promise<LoginResponseDto> {
    const result = await this.authService.handleCallback(code);

    response.cookie(AUTH_COOKIE_NAME, result.sessionToken, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
    });

    return { url: result.redirectUrl };
  }

  @Post('logout')
  @HttpCode(HttpStatus.OK)
  @ApiCookieAuth()
  @ApiOperation({ summary: 'Clear the authentication cookie.' })
  @ApiResponse({ status: 200, type: LoginResponseDto })
  logout(@Res({ passthrough: true }) response: Response): LoginResponseDto {
    response.clearCookie(AUTH_COOKIE_NAME);
    return { url: '/login' };
  }

  @Get('me')
  @ApiCookieAuth()
  @ApiOperation({ summary: 'Return the current authenticated user.' })
  @ApiResponse({ status: 200, type: AuthUserResponseDto })
  me(@CurrentUser() user: AuthenticatedUser): AuthUserResponseDto {
    return user;
  }
}
