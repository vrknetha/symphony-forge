#!/usr/bin/env bash
# Tear down an isolated worktree and its infra.
# Usage: ./scripts/teardown-worktree.sh <branch-name>
set -euo pipefail

BRANCH="${1:?Usage: teardown-worktree.sh <branch-name>}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKTREE_DIR="$(dirname "$ROOT_DIR")/worktrees/$BRANCH"

# Reconstruct ports from branch name
HASH=$(echo -n "$BRANCH" | shasum | awk '{print $1}')
HASH_INT=$(( 16#${HASH:0:8} % 1000 ))
BASE_PORT=$(( 3000 + HASH_INT * 10 ))
export DB_PORT=$(( BASE_PORT + 2 ))
export REDIS_PORT=$(( BASE_PORT + 3 ))
export DB_NAME="sf_${BRANCH//[-\/]/_}"
export WORKTREE_NAME="$BRANCH"

echo "▸ Stopping infra for $BRANCH..."
if [[ -f "$WORKTREE_DIR/docker-compose.yml" ]]; then
  cd "$WORKTREE_DIR"
  docker compose -f docker-compose.yml -f docker-compose.worktree.yml down -v 2>/dev/null || true
fi

echo "▸ Removing worktree..."
cd "$ROOT_DIR"
git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || rm -rf "$WORKTREE_DIR"
git branch -D "$BRANCH" 2>/dev/null || true

echo "✓ Worktree $BRANCH removed."
