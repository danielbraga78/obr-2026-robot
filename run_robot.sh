#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

cd "$SCRIPT_DIR"

if [[ -x "$PYTHON_BIN" ]]; then
    echo "Usando Python em: $PYTHON_BIN"
    exec "$PYTHON_BIN" -u raspberry/main.py
else
    echo "Python do projeto não foi encontrado: $PYTHON_BIN" >&2
    echo "Crie o ambiente com: python3 -m venv --system-site-packages $SCRIPT_DIR/.venv" >&2
    exit 1
fi
