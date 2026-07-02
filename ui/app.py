"""Точка входа десклета: связывает Sampler (core) с MainWindow (ui) через QTimer."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.config import SamplerConfig
from core.sampler import Sampler
from ui.widget.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sampler = Sampler(SamplerConfig(interval_ms=1000))
    sampler.on_sample(window.update_snapshot)

    timer = QTimer()
    timer.setInterval(sampler.config.interval_ms)
    timer.timeout.connect(sampler.tick)
    timer.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
