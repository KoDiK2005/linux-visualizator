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
        self._filter: list[str] = []
        self._scale = 1.0
        self._accent_color = theme.ACCENT_DISK
        self.setMinimumHeight(BAR_HEIGHT + 4)

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.updateGeometry()
        self.update()

    def set_color(self, accent_color: str) -> None:
        self._accent_color = accent_color
        self.update()

    def set_filter(self, filter_text: str) -> None:
        """Список подстрок точек монтирования через запятую; пусто = показывать все."""
        self._filter = [part.strip() for part in filter_text.split(",") if part.strip()]
        self.updateGeometry()
        self.update()

    def update_snapshot(self, disk: DiskSnapshot) -> None:
        self._partitions = self._apply_filter(disk.partitions)
        self.updateGeometry()
        self.update()

    def _apply_filter(self, partitions: list[PartitionUsage]) -> list[PartitionUsage]:
        if not self._filter:
            return partitions
        return [p for p in partitions if any(f in p.mountpoint for f in self._filter)]

    def sizeHint(self) -> QSize:
        bar_height = BAR_HEIGHT * self._scale
        bar_spacing = BAR_SPACING * self._scale
        count = max(len(self._partitions), 1)
        height = count * bar_height + max(count - 1, 0) * bar_spacing
        return QSize(200, round(height))

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        bar_height = BAR_HEIGHT * self._scale
        bar_spacing = BAR_SPACING * self._scale

        for idx, partition in enumerate(self._partitions):
            y = idx * (bar_height + bar_spacing)
            label = f"{_short_label(partition.mountpoint)} {partition.percent:.0f}%"
            self._draw_bar(painter, y, width, bar_height, partition.percent, label)

    def _draw_bar(
        self, painter: QPainter, y: float, width: float, bar_height: float, percent: float, label: str,
    ) -> None:
        bg_rect = QRectF(0, y, width, bar_height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(bg_rect, 4, 4)

        fill_color = severity_color(self._accent_color, percent)
        fill_width = width * min(percent, 100.0) / 100.0
        fill_rect = QRectF(0, y, fill_width, bar_height)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 4, 4)

        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, round(6 * self._scale)))
        painter.drawText(bg_rect, Qt.AlignCenter, label)
