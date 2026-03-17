#!/usr/bin/env bash
# Create an isolated git worktree with dedicated infra.
# Usage: ./scripts/setup-worktree.sh <branch-name>
set -euo pipefail

BRANCH="${1:?Usage: setup-worktree.sh <branch-name>}"
MAX_WORKTREES="${SYMPHONY_MAX_WORKTREES:-4}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKTREE_DIR="$(dirname "$ROOT_DIR")/worktrees/$BRANCH"

# Check concurrency limit
ACTIVE=$(git worktree list --porcelain | grep -c '^worktree ' || true)
if (( ACTIVE > MAX_WORKTREES )); then
  echo "ERROR: $ACTIVE worktrees active (max $MAX_WORKTREES). Teardown one first."
  exit 1
fi

# Deterministic port allocation from branch name hash
HASH=$(echo -n "$BRANCH" | shasum | awk '{print $1}')
HASH_INT=$(( 16#${HASH:0:8} % 1000 ))
BASE_PORT=$(( 3000 + HASH_INT * 10 ))

export API_PORT=$(( BASE_PORT + 0 ))
export WEB_PORT=$(( BASE_PORT + 1 ))
export DB_PORT=$(( BASE_PORT + 2 ))
export REDIS_PORT=$(( BASE_PORT + 3 ))
export DB_NAME="sf_${BRANCH//[-\/]/_}"
export WORKTREE_NAME="$BRANCH"

echo "▸ Creating worktree: $BRANCH"
echo "  API=$API_PORT  WEB=$WEB_PORT  DB=$DB_PORT  Redis=$REDIS_PORT"

git worktree add "$WORKTREE_DIR" -b "$BRANCH" 2>/dev/null || \
  git worktree add "$WORKTREE_DIR" "$BRANCH"

# Write .env for this worktree
cat > "$WORKTREE_DIR/.env" <<EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:${DB_PORT}/${DB_NAME}
REDIS_URL=redis://localhost:${REDIS_PORT}
API_PORT=${API_PORT}
WEB_PORT=${WEB_PORT}
DB_PORT=${DB_PORT}
REDIS_PORT=${REDIS_PORT}
DB_NAME=${DB_NAME}
WORKTREE_NAME=${WORKTREE_NAME}
NODE_ENV=development
EOF

# Start isolated infra
cd "$WORKTREE_DIR"
docker compose -f docker-compose.yml -f docker-compose.worktree.yml up -d --wait

# Install + migrate
pnpm install --frozen-lockfile
pnpm --filter @symphony/api prisma:generate
pnpm --filter @symphony/api prisma:deploy

echo "✓ Worktree ready at: $WORKTREE_DIR"
echo "  cd $WORKTREE_DIR && pnpm dev"
