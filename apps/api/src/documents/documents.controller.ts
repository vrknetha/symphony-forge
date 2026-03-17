import { Body, Controller, Delete, Get, Param, Patch, Post } from '@nestjs/common';
import { ApiCookieAuth, ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import type { AuthenticatedUser } from '@symphony/shared';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { CreateDocumentDto } from './dto/create-document.dto';
import { DocumentResponseDto } from './dto/document-response.dto';
import { UpdateDocumentDto } from './dto/update-document.dto';
import { DocumentsService } from './documents.service';

@ApiTags('Documents')
@ApiCookieAuth()
@Controller('api/v1/projects/:slug/documents')
export class DocumentsController {
  constructor(private readonly documentsService: DocumentsService) {}

  @Get()
  @ApiOperation({ summary: 'List documents in a project.' })
  @ApiResponse({ status: 200, type: [DocumentResponseDto] })
  list(@Param('slug') slug: string, @CurrentUser() user: AuthenticatedUser) {
    return this.documentsService.list(slug, user);
  }

  @Post()
  @ApiOperation({ summary: 'Create a project document and Proof backing document.' })
  @ApiResponse({ status: 201, type: DocumentResponseDto })
  create(
    @Param('slug') slug: string,
    @Body() dto: CreateDocumentDto,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.documentsService.create(slug, dto, user);
  }

  @Get(':documentSlug')
  @ApiOperation({ summary: 'Fetch document metadata by slug.' })
  @ApiResponse({ status: 200, type: DocumentResponseDto })
  detail(
    @Param('slug') slug: string,
    @Param('documentSlug') documentSlug: string,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.documentsService.detail(slug, documentSlug, user);
  }

  @Patch(':documentSlug')
  @ApiOperation({ summary: 'Update document metadata.' })
  @ApiResponse({ status: 200, type: DocumentResponseDto })
  update(
    @Param('slug') slug: string,
    @Param('documentSlug') documentSlug: string,
    @Body() dto: UpdateDocumentDto,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.documentsService.update(slug, documentSlug, dto, user);
  }

  @Delete(':documentSlug')
  @ApiOperation({ summary: 'Soft delete a document.' })
  @ApiResponse({ status: 200, type: DocumentResponseDto })
  async remove(
    @Param('slug') slug: string,
    @Param('documentSlug') documentSlug: string,
    @CurrentUser() user: AuthenticatedUser,
  ): Promise<{ deleted: boolean }> {
    await this.documentsService.remove(slug, documentSlug, user);
    return { deleted: true };
  }
}
