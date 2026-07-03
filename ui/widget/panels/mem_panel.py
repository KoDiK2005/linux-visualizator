"""Полосы заполнения для RAM и Swap."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from core.models import MemorySnapshot
from ui.widget import theme
from ui.widget.animation import SmoothedValue
from ui.widget.severity import severity_color

BAR_HEIGHT = 12
BAR_SPACING = 4
BYTES_PER_GB = 1024**3


class MemPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mem_percent = SmoothedValue()
        self._swap_percent = SmoothedValue()
        self._total_bytes = 0
        self._used_bytes = 0
        self._has_swap = False
        self._scale = 1.0
        self._accent_color = theme.ACCENT_MEM
        self.setMinimumHeight(BAR_HEIGHT + 4)

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.updateGeometry()
        self.update()

    def set_color(self, accent_color: str) -> None:
        self._accent_color = accent_color
        self.update()

    def update_snapshot(self, memory: MemorySnapshot) -> None:
        self._mem_percent.set_target(memory.percent)
        self._swap_percent.set_target(memory.swap_percent)
        self._total_bytes = memory.total_bytes
        self._used_bytes = memory.used_bytes
        self._has_swap = memory.swap_total_bytes > 0
        self.updateGeometry()

    def animate(self) -> bool:
        changed = self._mem_percent.step() | self._swap_percent.step()
        if changed:
            self.update()
        return changed

    def sizeHint(self) -> QSize:
        bar_height = BAR_HEIGHT * self._scale
        bar_spacing = BAR_SPACING * self._scale
        height = bar_height + (bar_height + bar_spacing if self._has_swap else 0) + 4
        return QSize(200, round(height))

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        bar_height = BAR_HEIGHT * self._scale
        bar_spacing = BAR_SPACING * self._scale

        ram_label = f"RAM {self._mem_percent.value:.0f}%"
        if self._total_bytes:
            used_gb = self._used_bytes / BYTES_PER_GB
            total_gb = self._total_bytes / BYTES_PER_GB
            ram_label += f"  ({used_gb:.1f}/{total_gb:.1f} GB)"

        self._draw_bar(
            painter, 0, width, bar_height, self._mem_percent.value, ram_label,
            severity_color(self._accent_color, self._mem_percent.value),
        )
        if self._has_swap:
            self._draw_bar(
                painter, bar_height + bar_spacing, width, bar_height, self._swap_percent.value,
                f"SWAP {self._swap_percent.value:.0f}%", QColor(self._accent_color), dim=True,
            )

    def _draw_bar(
        self, painter: QPainter, y: float, width: float, bar_height: float, percent: float,
        label: str, color: QColor, dim: bool = False,
    ) -> None:
        bg_rect = QRectF(0, y, width, bar_height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(bg_rect, 4, 4)

        fill_color = QColor(color)
        if dim:
            fill_color.setAlpha(140)
        fill_width = width * min(percent, 100.0) / 100.0
        fill_rect = QRectF(0, y, fill_width, bar_height)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 4, 4)

        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, round(6 * self._scale)))
        painter.drawText(bg_rect, Qt.AlignCenter, label)
