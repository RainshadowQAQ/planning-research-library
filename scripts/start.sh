#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
if [ ! -f web/vendor/pdfjs/build/pdf.mjs ]; then
  npm ci --ignore-scripts
  npm run vendor
fi
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PLANNING_PORT:-8765}"
