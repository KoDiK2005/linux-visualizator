"""Спарклайн сетевого трафика (приём/отправка) по последним замерам."""

from collections import deque

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from core.models import NetworkSnapshot
from ui.widget import theme

HISTORY_LEN = 60
PANEL_HEIGHT = 40
LABEL_HEIGHT = 14


class NetPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recv_history: deque[float] = deque(maxlen=HISTORY_LEN)
        self._sent_history: deque[float] = deque(maxlen=HISTORY_LEN)
        self.setMinimumHeight(PANEL_HEIGHT)

    def update_snapshot(self, network: NetworkSnapshot) -> None:
        recv = sum(i.bytes_recv_per_sec for i in network.interfaces)
        sent = sum(i.bytes_sent_per_sec for i in network.interfaces)
        self._recv_history.append(recv)
        self._sent_history.append(sent)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()

        max_value = max([*self._recv_history, *self._sent_history, 1.0])

        self._draw_line(painter, self._recv_history, max_value, width, height, theme.ACCENT_NET)
        self._draw_line(painter, self._sent_history, max_value, width, height, theme.ACCENT_CPU)

        current_recv = self._recv_history[-1] if self._recv_history else 0.0
        current_sent = self._sent_history[-1] if self._sent_history else 0.0
        painter.setPen(QColor(theme.TEXT_COLOR))
        painter.setFont(QFont(theme.FONT_FAMILY, 7))
        painter.drawText(
            QRectF(0, 0, width, LABEL_HEIGHT),
            Qt.AlignLeft,
            f"↓{current_recv / 1024:5.1f} KB/s  ↑{current_sent / 1024:5.1f} KB/s",
        )

    def _draw_line(
        self,
        painter: QPainter,
        history: deque[float],
        max_value: float,
        width: float,
        height: float,
        color: str,
    ) -> None:
        if len(history) < 2:
            return
        step = width / (HISTORY_LEN - 1)
        offset = HISTORY_LEN - len(history)
        plot_top = LABEL_HEIGHT
        plot_height = height - plot_top - 2

        path = QPainterPath()
        for idx, value in enumerate(history):
            x = (offset + idx) * step
            y = plot_top + plot_height - (value / max_value) * plot_height
            if idx == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.setPen(QPen(QColor(color), 1.5))
        painter.drawPath(path)
