#!/usr/bin/env bash
# Boot script — start infra, install, migrate, seed, run dev servers.
# Usage: ./scripts/boot.sh [--no-seed]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

NO_SEED=false
[[ "${1:-}" == "--no-seed" ]] && NO_SEED=true

echo "▸ Starting infrastructure..."
docker compose up -d --wait

echo "▸ Installing dependencies..."
pnpm install --frozen-lockfile

echo "▸ Generating Prisma client..."
pnpm --filter @symphony/api prisma:generate

echo "▸ Running migrations..."
pnpm --filter @symphony/api prisma:deploy

if [[ "$NO_SEED" == false ]]; then
  echo "▸ Seeding database..."
  pnpm --filter @symphony/api prisma:seed
fi

echo "▸ Building shared packages..."
pnpm --filter @symphony/shared build

echo "✓ Ready. Run: pnpm dev"
