"""Пользовательские настройки десклета: что показывать и как часто опрашивать."""

from dataclasses import dataclass

from PySide6.QtCore import QSettings

MIN_INTERVAL_MS = 200
MAX_INTERVAL_MS = 5000
DEFAULT_INTERVAL_MS = 1000


@dataclass
class AppSettings:
    interval_ms: int = DEFAULT_INTERVAL_MS
    show_cpu: bool = True
    show_mem: bool = True
    show_net: bool = True


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
    )


def save_settings(settings: QSettings, app_settings: AppSettings) -> None:
    settings.setValue("settings/interval_ms", app_settings.interval_ms)
    settings.setValue("settings/show_cpu", app_settings.show_cpu)
    settings.setValue("settings/show_mem", app_settings.show_mem)
    settings.setValue("settings/show_net", app_settings.show_net)
