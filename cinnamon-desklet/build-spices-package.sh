#!/usr/bin/env bash
# Собирает пакет для отправки в linuxmint/cinnamon-spices-desklets из канонических
# исходников в linux-visualizator@KoDiK2005/, чтобы не поддерживать два копии кода.
# Структура на выходе соответствует их validate-spice: UUID/{info.json,screenshot.png,
# README.md,files/UUID/{metadata.json,desklet.js,settings-schema.json,icon.png}}.
set -euo pipefail

UUID="linux-visualizator@KoDiK2005"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/$UUID"
OUT_DIR="$SCRIPT_DIR/dist/spices/$UUID"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/files/$UUID"

cp "$SOURCE_DIR/metadata.json" "$OUT_DIR/files/$UUID/"
cp "$SOURCE_DIR/desklet.js" "$OUT_DIR/files/$UUID/"
cp "$SOURCE_DIR/settings-schema.json" "$OUT_DIR/files/$UUID/"
cp "$SOURCE_DIR/icon.png" "$OUT_DIR/files/$UUID/"

cp "$SCRIPT_DIR/spices-submission/info.json" "$OUT_DIR/"
cp "$SCRIPT_DIR/spices-submission/README.md" "$OUT_DIR/"
if [ -f "$SCRIPT_DIR/spices-submission/screenshot.png" ]; then
    cp "$SCRIPT_DIR/spices-submission/screenshot.png" "$OUT_DIR/"
else
    echo "ПРЕДУПРЕЖДЕНИЕ: нет spices-submission/screenshot.png — добавьте перед отправкой." >&2
fi

echo "Собрано: $OUT_DIR"
