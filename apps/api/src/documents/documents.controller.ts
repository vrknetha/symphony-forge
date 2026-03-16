import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  Query,
} from '@nestjs/common';
import {
  ApiCreatedResponse,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from '@nestjs/swagger';
import { CurrentUser } from '../common/decorators/current-user.decorator';
import { AuthenticatedUser } from '../common/types/authenticated-user';
import { CreateDocumentDto } from './dto/create-document.dto';
import { DocumentResponseDto } from './dto/document-response.dto';
import { ListDocumentsQueryDto } from './dto/list-documents-query.dto';
import { UpdateDocumentDto } from './dto/update-document.dto';
import { DocumentsService } from './documents.service';

@ApiTags('Documents')
@Controller('projects/:slug/documents')
export class DocumentsController {
  constructor(private readonly service: DocumentsService) {}

  @Post()
  @ApiCreatedResponse({ type: DocumentResponseDto })
  @ApiOperation({
    summary: 'Create a document and corresponding Proof SDK document',
  })
  create(
    @Body() dto: CreateDocumentDto,
    @CurrentUser() user: AuthenticatedUser,
    @Param('slug') projectSlug: string,
  ) {
    return this.service.createDocument(dto, projectSlug, user);
  }

  @Delete(':docSlug')
  @ApiOkResponse({ schema: { example: { success: true } } })
  @ApiOperation({ summary: 'Soft delete a document' })
  deleteDocument(
    @CurrentUser() user: AuthenticatedUser,
    @Param('docSlug') docSlug: string,
    @Param('slug') projectSlug: string,
  ) {
    return this.service.deleteDocument(docSlug, projectSlug, user);
  }

  @Get()
  @ApiOkResponse({ type: [DocumentResponseDto] })
  @ApiOperation({ summary: 'List documents in a project' })
  list(
    @CurrentUser() user: AuthenticatedUser,
    @Param('slug') projectSlug: string,
    @Query() query: ListDocumentsQueryDto,
  ) {
    return this.service.listDocuments(projectSlug, query, user);
  }

  @Get(':docSlug')
  @ApiOkResponse({ type: DocumentResponseDto })
  @ApiOperation({ summary: 'Get a document by slug' })
  getDocument(
    @CurrentUser() user: AuthenticatedUser,
    @Param('docSlug') docSlug: string,
    @Param('slug') projectSlug: string,
  ) {
    return this.service.getDocument(docSlug, projectSlug, user);
  }

  @Patch(':docSlug')
  @ApiOkResponse({ type: DocumentResponseDto })
  @ApiOperation({ summary: 'Update document metadata' })
  updateDocument(
    @Body() dto: UpdateDocumentDto,
    @CurrentUser() user: AuthenticatedUser,
    @Param('docSlug') docSlug: string,
    @Param('slug') projectSlug: string,
  ) {
    return this.service.updateDocument(docSlug, dto, projectSlug, user);
  }
}
