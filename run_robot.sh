#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Aceita um ambiente virtual do projeto ou um externo, como:
# /home/leosouza/Desktop/trabalho/.venv
PYTHON_BIN=""

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif [[ -x "/home/leosouza/Desktop/trabalho/.venv/bin/python" ]]; then
    PYTHON_BIN="/home/leosouza/Desktop/trabalho/.venv/bin/python"
fi

cd "$SCRIPT_DIR"

if [[ -n "$PYTHON_BIN" && -x "$PYTHON_BIN" ]]; then
    echo "Usando Python em: $PYTHON_BIN"
    "$PYTHON_BIN" raspberry/main.py
else
    echo "Nenhum ambiente virtual válido foi encontrado."
    echo "Crie ou ative um ambiente virtual e tente novamente."
    echo "Exemplo: python3 -m venv /home/leosouza/Desktop/trabalho/.venv"
    exit 1
fi
