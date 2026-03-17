#!/usr/bin/env bash
# Generate typed frontend API client from OpenAPI spec.
# Usage: ./scripts/generate-api-client.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

SPEC_FILE="apps/api/openapi.json"

echo "▸ Generating OpenAPI spec..."
pnpm --filter @symphony/api generate:openapi

if [[ ! -f "$SPEC_FILE" ]]; then
  echo "ERROR: $SPEC_FILE not generated. Check apps/api/src/openapi.ts"
  exit 1
fi

echo "▸ Running orval..."
npx orval --input "$SPEC_FILE" --output apps/web/src/lib/api/generated.ts

echo "✓ API client generated at apps/web/src/lib/api/generated.ts"
