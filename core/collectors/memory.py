"""Сбор метрик оперативной памяти и swap."""

import psutil

from core.models import MemorySnapshot


def collect() -> MemorySnapshot:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return MemorySnapshot(
        total_bytes=vm.total,
        used_bytes=vm.used,
        percent=vm.percent,
        swap_total_bytes=swap.total,
        swap_used_bytes=swap.used,
        swap_percent=swap.percent,
    )
