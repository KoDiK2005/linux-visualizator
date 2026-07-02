"""Сбор метрик CPU: общая и по-ядерная загрузка, частота, температура."""

import psutil

from core.models import CpuSnapshot


def _read_temperature_c() -> float | None:
    temps = psutil.sensors_temperatures()
    for label in ("coretemp", "k10temp", "cpu_thermal"):
        entries = temps.get(label)
        if entries:
            return entries[0].current
    return None


def collect() -> CpuSnapshot:
    total = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    freq = psutil.cpu_freq()
    return CpuSnapshot(
        total_percent=total,
        per_core_percent=per_core,
        frequency_mhz=freq.current if freq else None,
        temperature_c=_read_temperature_c(),
    )
