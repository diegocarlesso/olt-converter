#!/usr/bin/env bash
# Script de inicialização do frontend (Linux/macOS)
set -e
cd "$(dirname "$0")/frontend"

if [ ! -d node_modules ]; then
  echo "Instalando dependencias..."
  npm install
fi
npm run dev
