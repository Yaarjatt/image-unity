#!/bin/bash
# Image Unity - Quick Start
set -e
echo ""
echo "  Image Unity - Quick Start"
echo ""

if ! command -v node &> /dev/null; then
  echo "Node.js required. Install from https://nodejs.org"
  exit 1
fi
echo "Node.js $(node -v)"

if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install express --no-audit --no-fund
fi

mkdir -p uploads

if [ -f .env ]; then
  set -a; source .env; set +a
  echo "Loaded .env"
fi

echo ""
echo "  Starting server..."
echo "  Web UI:  http://localhost:${PORT:-3777}"
echo "  API:     http://localhost:${PORT:-3777}/api"
echo "  Health:  http://localhost:${PORT:-3777}/api/health"
echo ""

node server/index.js
