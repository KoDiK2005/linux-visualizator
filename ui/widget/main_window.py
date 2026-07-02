"""Прозрачное frameless-окно десклета, которое можно перетаскивать по рабочему столу."""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.models import SystemSnapshot
from ui.widget import theme


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(
            f"background-color: {theme.BACKGROUND_COLOR}; "
            f"color: {theme.TEXT_COLOR}; "
            f"font-family: {theme.FONT_FAMILY}; "
            f"font-size: {theme.FONT_SIZE_PT}pt; "
            "border-radius: 12px;"
        )

        self._drag_offset: QPoint | None = None

        self.cpu_label = QLabel("CPU: --%")
        self.mem_label = QLabel("RAM: --%")
        self.net_label = QLabel("NET: -- / -- KB/s")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.mem_label)
        layout.addWidget(self.net_label)

        self.resize(220, 100)

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        self.cpu_label.setText(f"CPU: {snapshot.cpu.total_percent:5.1f}%")
        self.mem_label.setText(f"RAM: {snapshot.memory.percent:5.1f}%")

        total_sent = sum(i.bytes_sent_per_sec for i in snapshot.network.interfaces)
        total_recv = sum(i.bytes_recv_per_sec for i in snapshot.network.interfaces)
        self.net_label.setText(
            f"NET: ↑{total_sent / 1024:6.1f} KB/s  ↓{total_recv / 1024:6.1f} KB/s"
        )

    # Перетаскивание окна мышью, т.к. у frameless-окна нет заголовка.
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
