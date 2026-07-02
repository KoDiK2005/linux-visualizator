#!/usr/bin/env bash
# Регистрирует десклет в автозапуске текущего пользователя через .desktop-файл
# в ~/.config/autostart — подхватывается GNOME, KDE, XFCE, Cinnamon и т.д.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$REPO_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Не найдено виртуальное окружение $REPO_DIR/.venv" >&2
    echo "Сначала выполните: python3 -m venv .venv && .venv/bin/pip install -e ." >&2
    exit 1
fi

AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/linux-visualizator.desktop"
mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Linux Visualizator
Comment=Десктопный виджет с live-метриками CPU/RAM/сети
Exec=$VENV_PYTHON -m ui.app
Path=$REPO_DIR
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Автозапуск установлен: $DESKTOP_FILE"
echo "Виджет запустится автоматически при следующем входе в систему."
echo "Запустить прямо сейчас: $VENV_PYTHON -m ui.app &"
