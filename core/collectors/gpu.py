"""Сбор метрик GPU: загрузка, память, температура.

Поддерживает NVIDIA (через nvidia-smi) и AMD (через amdgpu sysfs). Если ни один
распознанный GPU не найден (например, чистый Intel iGPU без единого стандартного
интерфейса загрузки), collect() возвращает None — секция GPU скрывается в UI вместо
показа нулей.
"""

import glob
import subprocess

from core.models import GpuSnapshot


def _collect_nvidia() -> GpuSnapshot | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not line:
        return None
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 5:
        return None
    name, percent, mem_used_mb, mem_total_mb, temp_c = parts
    try:
        return GpuSnapshot(
            name=name,
            percent=float(percent),
            memory_used_bytes=int(float(mem_used_mb) * 1024 * 1024),
            memory_total_bytes=int(float(mem_total_mb) * 1024 * 1024),
            temperature_c=float(temp_c),
        )
    except ValueError:
        return None


def _read_int(path: str) -> int | None:
    try:
        with open(path) as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return None


def _collect_amd() -> GpuSnapshot | None:
    for busy_path in sorted(glob.glob("/sys/class/drm/card*/device/gpu_busy_percent")):
        percent = _read_int(busy_path)
        if percent is None:
            continue
        device_dir = busy_path.rsplit("/", 1)[0]
        mem_used = _read_int(f"{device_dir}/mem_info_vram_used") or 0
        mem_total = _read_int(f"{device_dir}/mem_info_vram_total") or 0
        temp_c = None
        for temp_path in glob.glob(f"{device_dir}/hwmon/hwmon*/temp1_input"):
            millidegrees = _read_int(temp_path)
            if millidegrees is not None:
                temp_c = millidegrees / 1000
                break
        return GpuSnapshot(
            name="AMD GPU",
            percent=float(percent),
            memory_used_bytes=mem_used,
            memory_total_bytes=mem_total,
            temperature_c=temp_c,
        )
    return None


def collect() -> GpuSnapshot | None:
    return _collect_nvidia() or _collect_amd()
