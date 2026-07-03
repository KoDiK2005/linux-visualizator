import subprocess

from core.collectors import gpu


def test_collect_returns_none_without_gpu_tools(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(gpu.glob, "glob", lambda pattern: [])

    assert gpu.collect() is None


def test_collect_parses_nvidia_smi_output(monkeypatch):
    class FakeResult:
        stdout = "NVIDIA GeForce RTX 3060, 42, 2048, 8192, 65\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())

    snapshot = gpu.collect()
    assert snapshot is not None
    assert snapshot.name == "NVIDIA GeForce RTX 3060"
    assert snapshot.percent == 42.0
    assert snapshot.memory_used_bytes == 2048 * 1024 * 1024
    assert snapshot.memory_total_bytes == 8192 * 1024 * 1024
    assert snapshot.temperature_c == 65.0


def test_collect_falls_back_to_amd_sysfs(monkeypatch, tmp_path):
    device_dir = tmp_path / "card0" / "device"
    device_dir.mkdir(parents=True)
    (device_dir / "gpu_busy_percent").write_text("17")
    (device_dir / "mem_info_vram_used").write_text(str(512 * 1024 * 1024))
    (device_dir / "mem_info_vram_total").write_text(str(4096 * 1024 * 1024))

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi not found")

    def fake_glob(pattern):
        if pattern.endswith("gpu_busy_percent"):
            return [str(device_dir / "gpu_busy_percent")]
        return []

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(gpu.glob, "glob", fake_glob)

    snapshot = gpu.collect()
    assert snapshot is not None
    assert snapshot.name == "AMD GPU"
    assert snapshot.percent == 17.0
    assert snapshot.memory_used_bytes == 512 * 1024 * 1024
    assert snapshot.memory_total_bytes == 4096 * 1024 * 1024
    assert snapshot.temperature_c is None
