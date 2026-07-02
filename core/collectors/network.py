"""Сбор метрик сетевого трафика по интерфейсам (байт/сек по дельте между опросами)."""

import time

import psutil

from core.models import InterfaceTraffic, NetworkSnapshot


class NetworkCollector:
    """Считает байт/сек по дельте счётчиков между последовательными вызовами collect()."""

    def __init__(self) -> None:
        self._last_counters: dict[str, psutil._common.snetio] = {}
        self._last_time: float | None = None

    def collect(self) -> NetworkSnapshot:
        now = time.monotonic()
        counters = psutil.net_io_counters(pernic=True)

        interfaces: list[InterfaceTraffic] = []
        elapsed = now - self._last_time if self._last_time else None

        for name, current in counters.items():
            previous = self._last_counters.get(name)
            if previous and elapsed:
                sent_rate = (current.bytes_sent - previous.bytes_sent) / elapsed
                recv_rate = (current.bytes_recv - previous.bytes_recv) / elapsed
            else:
                sent_rate = 0.0
                recv_rate = 0.0
            interfaces.append(
                InterfaceTraffic(
                    name=name,
                    bytes_sent_per_sec=max(sent_rate, 0.0),
                    bytes_recv_per_sec=max(recv_rate, 0.0),
                )
            )

        self._last_counters = counters
        self._last_time = now
        return NetworkSnapshot(interfaces=interfaces)
