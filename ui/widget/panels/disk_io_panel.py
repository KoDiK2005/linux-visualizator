"""Спарклайн скорости чтения/записи диска (I/O) по последним замерам."""

from core.models import DiskSnapshot
from ui.widget import theme
from ui.widget.panels.sparkline_panel import SparklinePanel


class DiskIoPanel(SparklinePanel):
    def __init__(self, parent=None) -> None:
        super().__init__(
            color_a=theme.ACCENT_DISK_READ,
            color_b=theme.ACCENT_DISK_WRITE,
            symbol_a="R",
            symbol_b="W",
            parent=parent,
        )

    def update_snapshot(self, disk: DiskSnapshot) -> None:
        self.update_values(disk.read_bytes_per_sec, disk.write_bytes_per_sec)
