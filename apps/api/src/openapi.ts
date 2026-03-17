import { NestFactory } from '@nestjs/core';
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';

async function generateOpenApi(): Promise<void> {
  const app = await NestFactory.create(AppModule, { logger: false });
  const config = new DocumentBuilder()
    .setTitle('Symphony Forge API')
    .setVersion('1.0.0')
    .build();
  const document = SwaggerModule.createDocument(app, config);

  await writeFile(
    join(process.cwd(), 'openapi.json'),
    JSON.stringify(document, null, 2),
    'utf8',
  );
  await app.close();
}

void generateOpenApi();
