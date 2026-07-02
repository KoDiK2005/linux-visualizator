"""Датаклассы-снапшоты системных метрик, возвращаемые коллекторами."""

from dataclasses import dataclass, field


@dataclass
class CpuSnapshot:
    total_percent: float
    per_core_percent: list[float]
    frequency_mhz: float | None = None
    temperature_c: float | None = None


@dataclass
class MemorySnapshot:
    total_bytes: int
    used_bytes: int
    percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_percent: float


@dataclass
class InterfaceTraffic:
    name: str
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float


@dataclass
class NetworkSnapshot:
    interfaces: list[InterfaceTraffic] = field(default_factory=list)


@dataclass
class PartitionUsage:
    mountpoint: str
    percent: float
    total_bytes: int
    used_bytes: int


@dataclass
class DiskSnapshot:
    partitions: list[PartitionUsage] = field(default_factory=list)
    read_bytes_per_sec: float = 0.0
    write_bytes_per_sec: float = 0.0


@dataclass
class SystemSnapshot:
    cpu: CpuSnapshot
    memory: MemorySnapshot
    network: NetworkSnapshot
    disk: DiskSnapshot
