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

    def update_snapshot(self, network: NetworkSnapshot) -> None:
        recv = sum(i.bytes_recv_per_sec for i in network.interfaces)
        sent = sum(i.bytes_sent_per_sec for i in network.interfaces)
        self.update_values(recv, sent)
