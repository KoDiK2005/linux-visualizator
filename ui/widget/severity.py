"""Подмешивает жёлтый/красный к базовому цвету при высокой загрузке.

Пороги настраиваются пользователем (по умолчанию 70/90, как и в cinnamon-desklet/):
0-warn% — обычный акцентный цвет, warn-bad% — переход к жёлтому,
bad-100% — переход от жёлтого к красному.
"""

from PySide6.QtGui import QColor

from ui.widget import theme

_warn_threshold = 70
_bad_threshold = 90


def set_thresholds(warn_threshold: int, bad_threshold: int) -> None:
    global _warn_threshold, _bad_threshold
    _warn_threshold = warn_threshold
    _bad_threshold = bad_threshold


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
    warn, bad = _warn_threshold, _bad_threshold
    if percent <= warn:
        return base
    warn_color = QColor(theme.ACCENT_WARN)
    if percent <= bad:
        span = max(bad - warn, 1)
        return _lerp_color(base, warn_color, (percent - warn) / span)
    bad_color = QColor(theme.ACCENT_BAD)
    return _lerp_color(warn_color, bad_color, min(1.0, (percent - bad) / 10))
