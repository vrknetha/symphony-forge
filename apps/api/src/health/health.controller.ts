import { Controller, Get } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Public } from '../common/decorators/public.decorator';

@ApiTags('Health')
@Controller('health')
export class HealthController {
  @Get()
  @Public()
  @ApiOperation({ summary: 'Check API health' })
  @ApiOkResponse({ schema: { example: { status: 'ok' } } })
  getHealth() {
    return { status: 'ok' };
  }
}
