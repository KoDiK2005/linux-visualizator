"""Полосы заполнения для RAM и Swap."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from core.models import MemorySnapshot
from ui.widget import theme
from ui.widget.animation import SmoothedValue

BAR_HEIGHT = 12
BAR_SPACING = 4


class MemPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mem_percent = SmoothedValue()
        self._swap_percent = SmoothedValue()
        self.setMinimumHeight(BAR_HEIGHT * 2 + BAR_SPACING + 4)

    def update_snapshot(self, memory: MemorySnapshot) -> None:
        self._mem_percent.set_target(memory.percent)
        self._swap_percent.set_target(memory.swap_percent)

    def animate(self) -> bool:
        changed = self._mem_percent.step() | self._swap_percent.step()
        if changed:
            self.update()
        return changed

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()

        self._draw_bar(painter, 0, width, self._mem_percent.value, "RAM", dim=False)
        self._draw_bar(
            painter, BAR_HEIGHT + BAR_SPACING, width, self._swap_percent.value, "SWAP", dim=True
        )

    def _draw_bar(
        self, painter: QPainter, y: float, width: float, percent: float, label: str, dim: bool
    ) -> None:
        bg_rect = QRectF(0, y, width, BAR_HEIGHT)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(bg_rect, 4, 4)

        fill_color = QColor(theme.ACCENT_MEM)
        if dim:
            fill_color.setAlpha(140)
        fill_width = width * min(percent, 100.0) / 100.0
        fill_rect = QRectF(0, y, fill_width, BAR_HEIGHT)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 4, 4)

        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, 6))
        painter.drawText(bg_rect, Qt.AlignCenter, f"{label} {percent:.0f}%")
