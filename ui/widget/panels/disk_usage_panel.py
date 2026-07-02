"""Полосы заполненности для каждого дискового раздела."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from core.models import DiskSnapshot, PartitionUsage
from ui.widget import theme
from ui.widget.severity import severity_color

BAR_HEIGHT = 12
BAR_SPACING = 4


def _short_label(mountpoint: str) -> str:
    if mountpoint == "/":
        return "/"
    return mountpoint.rstrip("/").rsplit("/", 1)[-1]


class DiskUsagePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._partitions: list[PartitionUsage] = []
        self.setMinimumHeight(BAR_HEIGHT + 4)

    def update_snapshot(self, disk: DiskSnapshot) -> None:
        self._partitions = disk.partitions
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        count = max(len(self._partitions), 1)
        height = count * BAR_HEIGHT + max(count - 1, 0) * BAR_SPACING
        return QSize(200, height)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()

        for idx, partition in enumerate(self._partitions):
            y = idx * (BAR_HEIGHT + BAR_SPACING)
            label = f"{_short_label(partition.mountpoint)} {partition.percent:.0f}%"
            self._draw_bar(painter, y, width, partition.percent, label)

    def _draw_bar(self, painter: QPainter, y: float, width: float, percent: float, label: str) -> None:
        bg_rect = QRectF(0, y, width, BAR_HEIGHT)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(bg_rect, 4, 4)

        fill_color = severity_color(theme.ACCENT_DISK, percent)
        fill_width = width * min(percent, 100.0) / 100.0
        fill_rect = QRectF(0, y, fill_width, BAR_HEIGHT)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 4, 4)

        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, 6))
        painter.drawText(bg_rect, Qt.AlignCenter, label)
