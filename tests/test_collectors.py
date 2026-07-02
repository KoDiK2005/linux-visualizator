from core.collectors import cpu, memory
from core.collectors.disk import DiskCollector
from core.collectors.network import NetworkCollector


def test_cpu_collect_returns_valid_snapshot():
    snapshot = cpu.collect()
    assert 0.0 <= snapshot.total_percent <= 100.0
    assert len(snapshot.per_core_percent) >= 1


def test_memory_collect_returns_valid_snapshot():
    snapshot = memory.collect()
    assert snapshot.total_bytes > 0
    assert 0.0 <= snapshot.percent <= 100.0


def test_network_collector_first_tick_has_zero_rate():
    collector = NetworkCollector()
    snapshot = collector.collect()
    assert len(snapshot.interfaces) >= 1
    assert all(i.bytes_sent_per_sec == 0.0 for i in snapshot.interfaces)


def test_disk_collector_first_tick_has_zero_rate():
    collector = DiskCollector()
    snapshot = collector.collect()
    assert len(snapshot.partitions) >= 1
    assert all(0.0 <= p.percent <= 100.0 for p in snapshot.partitions)
    assert snapshot.read_bytes_per_sec == 0.0
    assert snapshot.write_bytes_per_sec == 0.0
