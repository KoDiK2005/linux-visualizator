"""Периодический опрос коллекторов и хранение короткой истории снапшотов."""

from collections import deque
from collections.abc import Callable

from core.collectors import cpu, memory
from core.collectors.network import NetworkCollector
from core.config import SamplerConfig
from core.models import SystemSnapshot


class Sampler:
    """UI-агностичный сборщик: вызывает collect() по таймеру извне (например, из QTimer)
    и хранит последние history_length снапшотов для построения графиков.
    """

    def __init__(self, config: SamplerConfig | None = None) -> None:
        self.config = config or SamplerConfig()
        self._network_collector = NetworkCollector()
        self.history: deque[SystemSnapshot] = deque(maxlen=self.config.history_length)
        self._listeners: list[Callable[[SystemSnapshot], None]] = []

    def on_sample(self, callback: Callable[[SystemSnapshot], None]) -> None:
        self._listeners.append(callback)

    def tick(self) -> SystemSnapshot:
        snapshot = SystemSnapshot(
            cpu=cpu.collect(),
            memory=memory.collect(),
            network=self._network_collector.collect(),
        )
        self.history.append(snapshot)
        for listener in self._listeners:
            listener(snapshot)
        return snapshot
