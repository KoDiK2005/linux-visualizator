"""Прозрачное frameless-окно десклета, которое можно перетаскивать по рабочему столу."""

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMenu, QVBoxLayout, QWidget

from core.config import SamplerConfig
from core.models import SystemSnapshot
from core.sampler import Sampler
from ui.widget import severity, theme
from ui.widget.app_settings import AppSettings, load_settings, save_settings
from ui.widget.panels.cpu_panel import CpuPanel
from ui.widget.panels.disk_io_panel import DiskIoPanel
from ui.widget.panels.disk_usage_panel import DiskUsagePanel
from ui.widget.panels.mem_panel import MemPanel
from ui.widget.panels.net_panel import NetPanel
from ui.widget.settings_dialog import SettingsDialog

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
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._drag_offset: QPoint | None = None
        self._settings = QSettings(
            QSettings.IniFormat, QSettings.UserScope, "linux-visualizator", "desklet"
        )
        self._app_settings: AppSettings = load_settings(self._settings)

        self.cpu_panel = CpuPanel()
        self.mem_panel = MemPanel()
        self.net_panel = NetPanel()
        self.disk_usage_panel = DiskUsagePanel()
        self.disk_io_panel = DiskIoPanel()
        self._panel_groups = {
            "cpu": [self.cpu_panel],
            "mem": [self.mem_panel],
            "net": [self.net_panel],
            "disk": [self.disk_usage_panel, self.disk_io_panel],
        }

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(10)
        for panel in (
            self.cpu_panel, self.mem_panel, self.net_panel,
            self.disk_usage_panel, self.disk_io_panel,
        ):
            self._layout.addWidget(panel)

        self.setLayout(self._layout)
        self._apply_panel_visibility()
        self._apply_panel_order()
        self._apply_appearance_settings()
        self.adjustSize()
        self._restore_position()

        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(ANIMATION_INTERVAL_MS)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.start()

        self._sampler = Sampler(SamplerConfig(interval_ms=self._app_settings.interval_ms))
        self._sampler.on_sample(self.update_snapshot)
        self._sample_timer = QTimer(self)
        self._sample_timer.setInterval(self._app_settings.interval_ms)
        self._sample_timer.timeout.connect(self._sampler.tick)
        self._sample_timer.start()

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        self.cpu_panel.update_snapshot(snapshot.cpu)
        self.mem_panel.update_snapshot(snapshot.memory)
        self.net_panel.update_snapshot(snapshot.network)
        self.disk_usage_panel.update_snapshot(snapshot.disk)
        self.disk_io_panel.update_snapshot(snapshot.disk)
        # Число ядер/разделов известно только после первого тика, поэтому окно
        # пересчитывает размер под их содержимое здесь.
        self.adjustSize()

    def _animate(self) -> None:
        self.cpu_panel.animate()
        self.mem_panel.animate()

    def _apply_panel_visibility(self) -> None:
        self.cpu_panel.setVisible(self._app_settings.show_cpu)
        self.mem_panel.setVisible(self._app_settings.show_mem)
        self.net_panel.setVisible(self._app_settings.show_net)
        self.disk_usage_panel.setVisible(self._app_settings.show_disk)
        self.disk_io_panel.setVisible(self._app_settings.show_disk)

    def _apply_panel_order(self) -> None:
        order = [key.strip() for key in self._app_settings.panel_order.split(",") if key.strip()]
        seen = set(order)
        order += [key for key in self._panel_groups if key not in seen]
        for key in order:
            for panel in self._panel_groups.get(key, []):
                self._layout.removeWidget(panel)
                self._layout.addWidget(panel)

    def _apply_appearance_settings(self) -> None:
        severity.set_thresholds(
            self._app_settings.warn_threshold, self._app_settings.bad_threshold
        )
        scale = self._app_settings.ui_scale_percent / 100.0
        self.cpu_panel.set_scale(scale)
        self.mem_panel.set_scale(scale)
        self.net_panel.set_scale(scale)
        self.disk_usage_panel.set_scale(scale)
        self.disk_io_panel.set_scale(scale)
        self.disk_usage_panel.set_filter(self._app_settings.disk_filter)
        self.net_panel.set_interface_filter(self._app_settings.net_interfaces)
        self.net_panel.set_unit_mode(self._app_settings.net_unit)

    def _restore_position(self) -> None:
        saved = self._settings.value(SETTINGS_POSITION_KEY)
        if saved is not None:
            self.move(saved)

    def _save_position(self) -> None:
        self._settings.setValue(SETTINGS_POSITION_KEY, self.pos())

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        settings_action = menu.addAction("Настройки…")
        menu.addSeparator()
        quit_action = menu.addAction("Выход")

        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == settings_action:
            self._open_settings()
        elif chosen == quit_action:
            QApplication.instance().quit()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._app_settings, self)
        if dialog.exec() != SettingsDialog.Accepted:
            return

        new_settings = dialog.result_settings(self._app_settings)
        self._app_settings = new_settings
        save_settings(self._settings, new_settings)

        self._apply_panel_visibility()
        self._apply_panel_order()
        self._apply_appearance_settings()
        self.adjustSize()
        self._sample_timer.setInterval(new_settings.interval_ms)
        self._sampler.config.interval_ms = new_settings.interval_ms

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
