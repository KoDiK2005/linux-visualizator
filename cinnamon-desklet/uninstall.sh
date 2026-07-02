#!/usr/bin/env bash
set -euo pipefail

UUID="linux-visualizator@KoDiK2005"
TARGET_DIR="$HOME/.local/share/cinnamon/desklets/$UUID"

if [ -e "$TARGET_DIR" ] || [ -L "$TARGET_DIR" ]; then
    rm -rf "$TARGET_DIR"
    echo "Десклет удалён: $TARGET_DIR"
    echo "Не забудьте убрать его с рабочего стола (правый клик по десклету -> Убрать этот десклет)."
else
    echo "Десклет не установлен, нечего удалять."
fi
