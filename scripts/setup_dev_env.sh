#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python não encontrado: $PYTHON_BIN" >&2
  exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Criando ambiente virtual em $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "Atualizando ferramentas do ambiente virtual"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

echo "Instalando dependências do projeto"
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements-dev.txt"

echo

echo "Ambiente preparado com sucesso."
echo "Ative-o com:"
if [ -n "${SHELL:-}" ] && [[ "$SHELL" == */fish ]]; then
  echo "  source $VENV_DIR/bin/activate.fish"
else
  echo "  source $VENV_DIR/bin/activate"
fi
echo "Depois rode:"
echo "  python3 -m unittest discover -s tests -q"
