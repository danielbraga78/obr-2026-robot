#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="robot-obr.service"

if command -v systemctl >/dev/null 2>&1; then
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo "Parando o serviço $SERVICE_NAME via systemctl..."
        systemctl stop "$SERVICE_NAME"
    else
        echo "O serviço $SERVICE_NAME não está ativo."
    fi
else
    echo "systemctl não está disponível neste sistema."
    exit 1
fi

echo "Serviço finalizado somente por parada do sistema ou por este comando de stop."
