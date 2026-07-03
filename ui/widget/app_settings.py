"""Пользовательские настройки десклета: что показывать и как часто опрашивать."""

from dataclasses import dataclass

from PySide6.QtCore import QSettings

from ui.widget import theme

MIN_INTERVAL_MS = 200
MAX_INTERVAL_MS = 5000
DEFAULT_INTERVAL_MS = 1000

MIN_SCALE_PERCENT = 75
MAX_SCALE_PERCENT = 150
DEFAULT_SCALE_PERCENT = 100

DEFAULT_PANEL_ORDER = "cpu,mem,net,disk"


@dataclass
class AppSettings:
    interval_ms: int = DEFAULT_INTERVAL_MS
    show_cpu: bool = True
    show_mem: bool = True
    show_net: bool = True
    show_disk: bool = True
    warn_threshold: int = 70
    bad_threshold: int = 90
    disk_filter: str = ""
    net_unit: str = "bytes"
    net_interfaces: str = ""
    ui_scale_percent: int = DEFAULT_SCALE_PERCENT
    panel_order: str = DEFAULT_PANEL_ORDER
    accent_cpu: str = theme.ACCENT_CPU
    accent_mem: str = theme.ACCENT_MEM
    accent_net: str = theme.ACCENT_NET
    accent_disk: str = theme.ACCENT_DISK


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


def load_settings(settings: QSettings) -> AppSettings:
    return AppSettings(
        interval_ms=int(settings.value("settings/interval_ms", DEFAULT_INTERVAL_MS)),
        show_cpu=_to_bool(settings.value("settings/show_cpu", True)),
        show_mem=_to_bool(settings.value("settings/show_mem", True)),
        show_net=_to_bool(settings.value("settings/show_net", True)),
        show_disk=_to_bool(settings.value("settings/show_disk", True)),
        warn_threshold=int(settings.value("settings/warn_threshold", 70)),
        bad_threshold=int(settings.value("settings/bad_threshold", 90)),
        disk_filter=str(settings.value("settings/disk_filter", "")),
        net_unit=str(settings.value("settings/net_unit", "bytes")),
        net_interfaces=str(settings.value("settings/net_interfaces", "")),
        ui_scale_percent=int(settings.value("settings/ui_scale_percent", DEFAULT_SCALE_PERCENT)),
        panel_order=str(settings.value("settings/panel_order", DEFAULT_PANEL_ORDER)),
        accent_cpu=str(settings.value("settings/accent_cpu", theme.ACCENT_CPU)),
        accent_mem=str(settings.value("settings/accent_mem", theme.ACCENT_MEM)),
        accent_net=str(settings.value("settings/accent_net", theme.ACCENT_NET)),
        accent_disk=str(settings.value("settings/accent_disk", theme.ACCENT_DISK)),
    )


def save_settings(settings: QSettings, app_settings: AppSettings) -> None:
    settings.setValue("settings/interval_ms", app_settings.interval_ms)
    settings.setValue("settings/show_cpu", app_settings.show_cpu)
    settings.setValue("settings/show_mem", app_settings.show_mem)
    settings.setValue("settings/show_net", app_settings.show_net)
    settings.setValue("settings/show_disk", app_settings.show_disk)
    settings.setValue("settings/warn_threshold", app_settings.warn_threshold)
    settings.setValue("settings/bad_threshold", app_settings.bad_threshold)
    settings.setValue("settings/disk_filter", app_settings.disk_filter)
    settings.setValue("settings/net_unit", app_settings.net_unit)
    settings.setValue("settings/net_interfaces", app_settings.net_interfaces)
    settings.setValue("settings/ui_scale_percent", app_settings.ui_scale_percent)
    settings.setValue("settings/panel_order", app_settings.panel_order)
    settings.setValue("settings/accent_cpu", app_settings.accent_cpu)
    settings.setValue("settings/accent_mem", app_settings.accent_mem)
    settings.setValue("settings/accent_net", app_settings.accent_net)
    settings.setValue("settings/accent_disk", app_settings.accent_disk)
