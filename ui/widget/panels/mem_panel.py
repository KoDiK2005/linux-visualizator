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
        self.setMinimumHeight(BAR_HEIGHT + 4)

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
        height = BAR_HEIGHT + (BAR_HEIGHT + BAR_SPACING if self._has_swap else 0) + 4
        return QSize(200, height)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()

        ram_label = f"RAM {self._mem_percent.value:.0f}%"
        if self._total_bytes:
            used_gb = self._used_bytes / BYTES_PER_GB
            total_gb = self._total_bytes / BYTES_PER_GB
            ram_label += f"  ({used_gb:.1f}/{total_gb:.1f} GB)"

        self._draw_bar(
            painter, 0, width, self._mem_percent.value, ram_label,
            severity_color(theme.ACCENT_MEM, self._mem_percent.value),
        )
        if self._has_swap:
            self._draw_bar(
                painter, BAR_HEIGHT + BAR_SPACING, width, self._swap_percent.value,
                f"SWAP {self._swap_percent.value:.0f}%", QColor(theme.ACCENT_MEM), dim=True,
            )

    def _draw_bar(
        self, painter: QPainter, y: float, width: float, percent: float, label: str,
        color: QColor, dim: bool = False,
    ) -> None:
        bg_rect = QRectF(0, y, width, BAR_HEIGHT)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(bg_rect, 4, 4)

        fill_color = QColor(color)
        if dim:
            fill_color.setAlpha(140)
        fill_width = width * min(percent, 100.0) / 100.0
        fill_rect = QRectF(0, y, fill_width, BAR_HEIGHT)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 4, 4)

        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, 6))
        painter.drawText(bg_rect, Qt.AlignCenter, label)
