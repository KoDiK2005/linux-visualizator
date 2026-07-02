from core.collectors import cpu, memory
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
