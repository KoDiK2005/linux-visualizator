#!/usr/bin/env bash
# Устанавливает Linux Visualizator как нативный Cinnamon-десклет (для Linux Mint / Cinnamon).
set -euo pipefail

UUID="linux-visualizator@KoDiK2005"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/$UUID" && pwd)"
DESKLETS_DIR="$HOME/.local/share/cinnamon/desklets"
TARGET_DIR="$DESKLETS_DIR/$UUID"

mkdir -p "$DESKLETS_DIR"

if [ -e "$TARGET_DIR" ] || [ -L "$TARGET_DIR" ]; then
    rm -rf "$TARGET_DIR"
fi
ln -s "$SOURCE_DIR" "$TARGET_DIR"

echo "Десклет установлен: $TARGET_DIR -> $SOURCE_DIR"
echo
echo "Дальше добавьте его на рабочий стол:"
echo "  1. Правый клик по рабочему столу -> Десклеты"
echo "  2. Найдите «Linux Visualizator» в списке и нажмите «+» (добавить)"
echo
echo "Либо через терминал (замените INSTANCE_ID на свободный номер, X и Y — координаты):"
echo "  gsettings set org.cinnamon enabled-desklets \"\$(gsettings get org.cinnamon enabled-desklets | sed \"s/\\]\$/, '$UUID:INSTANCE_ID:X:Y']/\")\""
