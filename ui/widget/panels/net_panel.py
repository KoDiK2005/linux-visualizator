"""Спарклайн сетевого трафика (приём/отправка) по последним замерам."""

from core.models import NetworkSnapshot
from ui.widget import theme
from ui.widget.panels.sparkline_panel import SparklinePanel


class NetPanel(SparklinePanel):
    def __init__(self, parent=None) -> None:
        super().__init__(
            color_a=theme.ACCENT_NET,
            color_b=theme.ACCENT_CPU,
            symbol_a="↓",
            symbol_b="↑",
            parent=parent,
        )
        self._filter: list[str] = []

    def set_interface_filter(self, filter_text: str) -> None:
        """Список имён интерфейсов через запятую; пусто = суммировать все."""
        self._filter = [part.strip() for part in filter_text.split(",") if part.strip()]

    def update_snapshot(self, network: NetworkSnapshot) -> None:
        interfaces = network.interfaces
        if self._filter:
            interfaces = [i for i in interfaces if i.name in self._filter]
        recv = sum(i.bytes_recv_per_sec for i in interfaces)
        sent = sum(i.bytes_sent_per_sec for i in interfaces)
        self.update_values(recv, sent)
