#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Run acceptance tests using python3
cd "$REPO_ROOT"
python3 "$SCRIPT_DIR/tools/verify_runner.py"
