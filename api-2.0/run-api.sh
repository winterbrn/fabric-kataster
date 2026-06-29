#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

export PORT="${PORT:-4000}"

if [[ ! -d node_modules ]]; then
  npm install
fi

exec npm run start
