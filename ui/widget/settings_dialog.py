"""Диалог настроек десклета: интервал опроса, видимость панелей, внешний вид и тема."""

from dataclasses import replace

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widget import theme
from ui.widget.app_settings import (
    MAX_INTERVAL_MS,
    MAX_SCALE_PERCENT,
    MIN_INTERVAL_MS,
    MIN_SCALE_PERCENT,
    AppSettings,
)


class ColorButton(QPushButton):
    """Кнопка-образец цвета: клик открывает QColorDialog, хранит выбранный hex."""

    def __init__(self, color_hex: str, parent=None) -> None:
        super().__init__(parent)
        self._color_hex = color_hex
        self.setFixedWidth(70)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def color_hex(self) -> str:
        return self._color_hex

    def set_color(self, color_hex: str) -> None:
        self._color_hex = color_hex
        self._update_style()

    def _update_style(self) -> None:
        self.setText(self._color_hex)
        self.setStyleSheet(
            f"background-color: {self._color_hex}; color: #1a1a1a; border-radius: 4px;"
        )

    def _pick_color(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._color_hex), self, "Выберите цвет")
        if chosen.isValid():
            self.set_color(chosen.name())


class SettingsDialog(QDialog):
    def __init__(self, current: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки Linux Visualizator")

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(MIN_INTERVAL_MS, MAX_INTERVAL_MS)
        self.interval_spin.setSingleStep(100)
        self.interval_spin.setSuffix(" мс")
        self.interval_spin.setValue(current.interval_ms)

        self.show_cpu_check = QCheckBox("Показывать CPU")
        self.show_cpu_check.setChecked(current.show_cpu)
        self.show_mem_check = QCheckBox("Показывать RAM/Swap")
        self.show_mem_check.setChecked(current.show_mem)
        self.show_net_check = QCheckBox("Показывать сеть")
        self.show_net_check.setChecked(current.show_net)
        self.show_disk_check = QCheckBox("Показывать диски")
        self.show_disk_check.setChecked(current.show_disk)

        general_form = QFormLayout()
        general_form.addRow("Интервал опроса:", self.interval_spin)
        general_form.addRow(self.show_cpu_check)
        general_form.addRow(self.show_mem_check)
        general_form.addRow(self.show_net_check)
        general_form.addRow(self.show_disk_check)

        self.warn_spin = QSpinBox()
        self.warn_spin.setRange(1, 99)
        self.warn_spin.setSuffix(" %")
        self.warn_spin.setValue(current.warn_threshold)
        self.bad_spin = QSpinBox()
        self.bad_spin.setRange(2, 100)
        self.bad_spin.setSuffix(" %")
        self.bad_spin.setValue(current.bad_threshold)

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(MIN_SCALE_PERCENT, MAX_SCALE_PERCENT)
        self.scale_spin.setSingleStep(5)
        self.scale_spin.setSuffix(" %")
        self.scale_spin.setValue(current.ui_scale_percent)

        self.panel_order_edit = QLineEdit(current.panel_order)
        self.panel_order_edit.setPlaceholderText("cpu,mem,net,disk")

        appearance_form = QFormLayout()
        appearance_form.addRow("Жёлтый порог:", self.warn_spin)
        appearance_form.addRow("Красный порог:", self.bad_spin)
        appearance_form.addRow("Масштаб интерфейса:", self.scale_spin)
        appearance_form.addRow("Порядок панелей:", self.panel_order_edit)

        self.accent_cpu_button = ColorButton(current.accent_cpu)
        self.accent_mem_button = ColorButton(current.accent_mem)
        self.accent_net_button = ColorButton(current.accent_net)
        self.accent_disk_button = ColorButton(current.accent_disk)
        self.reset_theme_button = QPushButton("Сбросить тему")
        self.reset_theme_button.clicked.connect(self._reset_theme)

        theme_form = QFormLayout()
        theme_form.addRow("Цвет CPU:", self.accent_cpu_button)
        theme_form.addRow("Цвет RAM:", self.accent_mem_button)
        theme_form.addRow("Цвет сети:", self.accent_net_button)
        theme_form.addRow("Цвет дисков:", self.accent_disk_button)
        theme_form.addRow(self.reset_theme_button)

        self.disk_filter_edit = QLineEdit(current.disk_filter)
        self.disk_filter_edit.setPlaceholderText("например: /, /home (пусто = все)")

        self.net_unit_combo = QComboBox()
        self.net_unit_combo.addItem("Байты (KB/s)", "bytes")
        self.net_unit_combo.addItem("Биты (Kb/s)", "bits")
        unit_index = self.net_unit_combo.findData(current.net_unit)
        self.net_unit_combo.setCurrentIndex(max(unit_index, 0))

        self.net_interfaces_edit = QLineEdit(current.net_interfaces)
        self.net_interfaces_edit.setPlaceholderText("например: eth0,wlan0 (пусто = все)")

        data_form = QFormLayout()
        data_form.addRow("Разделы дисков:", self.disk_filter_edit)
        data_form.addRow("Единицы сети:", self.net_unit_combo)
        data_form.addRow("Интерфейсы сети:", self.net_interfaces_edit)

        tabs = QTabWidget()
        tabs.addTab(_wrap(general_form), "Основное")
        tabs.addTab(_wrap(appearance_form), "Внешний вид")
        tabs.addTab(_wrap(theme_form), "Тема")
        tabs.addTab(_wrap(data_form), "Данные")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _reset_theme(self) -> None:
        self.accent_cpu_button.set_color(theme.ACCENT_CPU)
        self.accent_mem_button.set_color(theme.ACCENT_MEM)
        self.accent_net_button.set_color(theme.ACCENT_NET)
        self.accent_disk_button.set_color(theme.ACCENT_DISK)

    def result_settings(self, base: AppSettings) -> AppSettings:
        warn = self.warn_spin.value()
        bad = self.bad_spin.value()
        if bad <= warn:
            bad = warn + 1
        return replace(
            base,
            interval_ms=self.interval_spin.value(),
            show_cpu=self.show_cpu_check.isChecked(),
            show_mem=self.show_mem_check.isChecked(),
            show_net=self.show_net_check.isChecked(),
            show_disk=self.show_disk_check.isChecked(),
            warn_threshold=warn,
            bad_threshold=bad,
            disk_filter=self.disk_filter_edit.text(),
            net_unit=self.net_unit_combo.currentData(),
            net_interfaces=self.net_interfaces_edit.text(),
            ui_scale_percent=self.scale_spin.value(),
            panel_order=self.panel_order_edit.text(),
            accent_cpu=self.accent_cpu_button.color_hex(),
            accent_mem=self.accent_mem_button.color_hex(),
            accent_net=self.accent_net_button.color_hex(),
            accent_disk=self.accent_disk_button.color_hex(),
        )


def _wrap(form: QFormLayout) -> QWidget:
    widget = QWidget()
    widget.setLayout(form)
    return widget
