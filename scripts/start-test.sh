#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PLANNING_TEST_MODE=1
export PLANNING_DATA_DIR="${PLANNING_DATA_DIR:-$PWD/.data-test}"
export PLANNING_PORT="${PLANNING_PORT:-8766}"
exec bash scripts/start.sh
