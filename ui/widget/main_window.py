"""Прозрачное frameless-окно десклета, которое можно перетаскивать по рабочему столу."""

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.models import SystemSnapshot
from ui.widget import theme
from ui.widget.panels.cpu_panel import CpuPanel
from ui.widget.panels.mem_panel import MemPanel
from ui.widget.panels.net_panel import NetPanel

ANIMATION_INTERVAL_MS = 33  # ~30 fps для плавных переходов значений
SETTINGS_POSITION_KEY = "window/position"


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
        self._settings = QSettings(
            QSettings.IniFormat, QSettings.UserScope, "linux-visualizator", "desklet"
        )

        self.cpu_panel = CpuPanel()
        self.mem_panel = MemPanel()
        self.net_panel = NetPanel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        layout.addWidget(self.cpu_panel)
        layout.addWidget(self.mem_panel)
        layout.addWidget(self.net_panel)

        self.setLayout(layout)
        self.adjustSize()
        self._restore_position()

        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(ANIMATION_INTERVAL_MS)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.start()

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        self.cpu_panel.update_snapshot(snapshot.cpu)
        self.mem_panel.update_snapshot(snapshot.memory)
        self.net_panel.update_snapshot(snapshot.network)
        # Число ядер известно только после первого тика, поэтому окно
        # пересчитывает размер под ширину кольцевых индикаторов CPU здесь.
        self.adjustSize()

    def _animate(self) -> None:
        self.cpu_panel.animate()
        self.mem_panel.animate()

    def _restore_position(self) -> None:
        saved = self._settings.value(SETTINGS_POSITION_KEY)
        if saved is not None:
            self.move(saved)

    def _save_position(self) -> None:
        self._settings.setValue(SETTINGS_POSITION_KEY, self.pos())

    # Перетаскивание окна мышью, т.к. у frameless-окна нет заголовка.
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if self._drag_offset is not None:
            self._drag_offset = None
            self._save_position()

    def closeEvent(self, event):
        self._save_position()
        super().closeEvent(event)
