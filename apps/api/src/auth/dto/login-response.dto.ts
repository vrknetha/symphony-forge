import { ApiProperty } from '@nestjs/swagger';

export class LoginResponseDto {
  @ApiProperty({ description: 'Azure authorize URL for the browser redirect.' })
  url!: string;
}
