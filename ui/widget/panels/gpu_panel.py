"""Полоса загрузки GPU с памятью и температурой."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from core.models import GpuSnapshot
from ui.widget import theme
from ui.widget.animation import SmoothedValue
from ui.widget.severity import severity_color

BAR_HEIGHT = 12
BYTES_PER_GB = 1024**3


class GpuPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._percent = SmoothedValue()
        self._memory_used_bytes = 0
        self._memory_total_bytes = 0
        self._temperature_c: float | None = None
        self._scale = 1.0
        self._accent_color = theme.ACCENT_GPU
        self.setMinimumHeight(BAR_HEIGHT + 4)

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.updateGeometry()
        self.update()

    def set_color(self, accent_color: str) -> None:
        self._accent_color = accent_color
        self.update()

    def update_snapshot(self, gpu: GpuSnapshot) -> None:
        self._percent.set_target(gpu.percent)
        self._memory_used_bytes = gpu.memory_used_bytes
        self._memory_total_bytes = gpu.memory_total_bytes
        self._temperature_c = gpu.temperature_c
        self.updateGeometry()

    def animate(self) -> bool:
        changed = self._percent.step()
        if changed:
            self.update()
        return changed

    def sizeHint(self) -> QSize:
        return QSize(200, round((BAR_HEIGHT + 4) * self._scale))

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        bar_height = BAR_HEIGHT * self._scale

        label = f"GPU {self._percent.value:.0f}%"
        if self._memory_total_bytes:
            used_gb = self._memory_used_bytes / BYTES_PER_GB
            total_gb = self._memory_total_bytes / BYTES_PER_GB
            label += f"  ({used_gb:.1f}/{total_gb:.1f} GB)"
        if self._temperature_c is not None:
            label += f"  {self._temperature_c:.0f}°C"

        bg_rect = QRectF(0, 0, width, bar_height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(bg_rect, 4, 4)

        fill_color = severity_color(self._accent_color, self._percent.value)
        fill_width = width * min(self._percent.value, 100.0) / 100.0
        fill_rect = QRectF(0, 0, fill_width, bar_height)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 4, 4)

        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, round(6 * self._scale)))
        painter.drawText(bg_rect, Qt.AlignCenter, label)
