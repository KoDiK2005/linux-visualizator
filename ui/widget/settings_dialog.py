"""Диалог настроек десклета: интервал опроса и видимость панелей."""

from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)

from ui.widget.app_settings import MAX_INTERVAL_MS, MIN_INTERVAL_MS, AppSettings


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

        form = QFormLayout()
        form.addRow("Интервал опроса:", self.interval_spin)
        form.addRow(self.show_cpu_check)
        form.addRow(self.show_mem_check)
        form.addRow(self.show_net_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def result_settings(self, base: AppSettings) -> AppSettings:
        return replace(
            base,
            interval_ms=self.interval_spin.value(),
            show_cpu=self.show_cpu_check.isChecked(),
            show_mem=self.show_mem_check.isChecked(),
            show_net=self.show_net_check.isChecked(),
        )
