"""Сбор метрик дисков: заполненность разделов и скорость чтения/записи (I/O)."""

import time

import psutil

from core.models import DiskSnapshot, PartitionUsage

MIN_PARTITION_SIZE_BYTES = 1 * 1024**3  # отсекаем крошечные разделы вроде /boot/efi


def _collect_partitions() -> list[PartitionUsage]:
    partitions: list[PartitionUsage] = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        if usage.total < MIN_PARTITION_SIZE_BYTES:
            continue
        partitions.append(
            PartitionUsage(
                mountpoint=part.mountpoint,
                percent=usage.percent,
                total_bytes=usage.total,
                used_bytes=usage.used,
            )
        )
    return partitions


class DiskCollector:
    """Считает байт/сек чтения и записи по дельте счётчиков между вызовами collect()."""

    def __init__(self) -> None:
        self._last_io: psutil._common.sdiskio | None = None
        self._last_time: float | None = None

    def collect(self) -> DiskSnapshot:
        now = time.monotonic()
        io = psutil.disk_io_counters()

        read_rate = 0.0
        write_rate = 0.0
        if io is not None and self._last_io is not None and self._last_time is not None:
            elapsed = now - self._last_time
            if elapsed > 0:
                read_rate = (io.read_bytes - self._last_io.read_bytes) / elapsed
                write_rate = (io.write_bytes - self._last_io.write_bytes) / elapsed

        self._last_io = io
        self._last_time = now

        return DiskSnapshot(
            partitions=_collect_partitions(),
            read_bytes_per_sec=max(read_rate, 0.0),
            write_bytes_per_sec=max(write_rate, 0.0),
        )
