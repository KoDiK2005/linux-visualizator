#!/usr/bin/env bash
set -euo pipefail

DESKTOP_FILE="$HOME/.config/autostart/linux-visualizator.desktop"

if [ -f "$DESKTOP_FILE" ]; then
    rm "$DESKTOP_FILE"
    echo "Автозапуск удалён: $DESKTOP_FILE"
else
    echo "Файл автозапуска не найден, нечего удалять."
fi
