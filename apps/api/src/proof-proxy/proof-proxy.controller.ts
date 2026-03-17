import { Controller, Get, Param, Req, Res, UseGuards } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { Request, Response } from 'express';
import { Public } from '../common/decorators/public.decorator';
import { ProofProxyGuard } from './proof-proxy.guard';
import { ProofProxyService } from './proof-proxy.service';

interface ProofRequest extends Request {
  agentKey?: Awaited<ReturnType<ProofProxyService['buildEditorUrl']>>;
  user?: Parameters<ProofProxyService['buildEditorUrl']>[0]['user'];
}

@ApiTags('Proof Proxy')
@Public()
@UseGuards(ProofProxyGuard)
@Controller('documents')
export class ProofProxyController {
  constructor(private readonly proofProxyService: ProofProxyService) {}

  @Get(':projectSlug/:documentSlug')
  @ApiOperation({ summary: 'Authorize and redirect to the Proof editor.' })
  async redirectToEditor(
    @Param('projectSlug') projectSlug: string,
    @Param('documentSlug') documentSlug: string,
    @Req() request: ProofRequest,
    @Res() response: Response,
  ): Promise<void> {
    const url = await this.proofProxyService.buildEditorUrl({
      documentSlug,
      projectSlug,
      user: request.user,
    });

    response.redirect(url);
  }
}
