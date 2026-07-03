"""Цвета, прозрачность и шрифты десклета."""

from PySide6.QtGui import QColor

BACKGROUND_COLOR = "rgba(20, 20, 25, 180)"
TEXT_COLOR = "#e0e0e0"
ACCENT_CPU = "#4fc3f7"
ACCENT_MEM = "#81c784"
ACCENT_NET = "#ffb74d"
ACCENT_DISK = "#ba68c8"
ACCENT_GPU = "#4dd0e1"
ACCENT_DISK_READ = "#ba68c8"
ACCENT_DISK_WRITE = "#e57373"
ACCENT_WARN = "#ffca28"
ACCENT_BAD = "#ef5350"
FONT_FAMILY = "Monospace"
FONT_SIZE_PT = 10


def lighten(hex_color: str, amount: float = 0.35) -> str:
    """Осветляет цвет к белому — используется для вторичной линии спарклайна
    (например, "отправлено"/"запись"), когда основной акцент задаётся пользователем."""
    color = QColor(hex_color)
    r = round(color.red() + (255 - color.red()) * amount)
    g = round(color.green() + (255 - color.green()) * amount)
    b = round(color.blue() + (255 - color.blue()) * amount)
    return QColor(r, g, b).name()
