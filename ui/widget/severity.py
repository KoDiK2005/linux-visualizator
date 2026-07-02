"""Подмешивает жёлтый/красный к базовому цвету при высокой загрузке.

Порог тот же, что и в cinnamon-desklet/.../desklet.js (severityColor), чтобы обе реализации
вели себя одинаково: 0-70% — обычный акцентный цвет, 70-90% — переход к жёлтому,
90-100% — переход от жёлтого к красному.
"""

from PySide6.QtGui import QColor

from ui.widget import theme


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        round(_lerp(c1.red(), c2.red(), t)),
        round(_lerp(c1.green(), c2.green(), t)),
        round(_lerp(c1.blue(), c2.blue(), t)),
    )


def severity_color(base_hex: str, percent: float) -> QColor:
    base = QColor(base_hex)
    if percent <= 70:
        return base
    warn = QColor(theme.ACCENT_WARN)
    if percent <= 90:
        return _lerp_color(base, warn, (percent - 70) / 20)
    bad = QColor(theme.ACCENT_BAD)
    return _lerp_color(warn, bad, min(1.0, (percent - 90) / 10))
