"""Конфигурация сбора метрик по умолчанию."""

from dataclasses import dataclass


@dataclass
class SamplerConfig:
    interval_ms: int = 1000
    history_length: int = 60  # сколько последних снапшотов хранить для спарклайнов
