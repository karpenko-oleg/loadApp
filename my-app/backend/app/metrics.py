import asyncio
from collections import deque
from collections.abc import Callable
from datetime import datetime
import os
from statistics import fmean
import time
from typing import Any

import psutil

from .models import MetricsSnapshot


class MetricsStore:
    def __init__(
        self,
        provider: Any = psutil,
        history_size: int = 600,
        root: str = "/",
        cgroup_root: str = "/sys/fs/cgroup",
        sample_interval: float = 1.0,
    ):
        self.provider = provider
        self.root = root
        self.cgroup_root = cgroup_root
        self.sample_interval = sample_interval
        self._history: deque[MetricsSnapshot] = deque(maxlen=history_size)
        self._api_requests = 0
        self._api_errors = 0
        self._latencies: deque[float] = deque(maxlen=1000)
        self._cgroup_cpu_previous: tuple[int, float] | None = None

    def collect(self) -> MetricsSnapshot:
        previous = self._history[-1] if self._history else MetricsSnapshot()
        memory_percent, memory_available_mb = self._memory_values(previous)
        snapshot = MetricsSnapshot(
            timestamp=datetime.now().astimezone(),
            cpu_percent=self._container_cpu_percent(previous.cpu_percent),
            load_1m=self._safe(lambda: float(self.provider.getloadavg()[0]), previous.load_1m),
            memory_percent=memory_percent,
            memory_available_mb=memory_available_mb,
            disk_usage_percent=self._safe(
                lambda: float(self.provider.disk_usage(self.root).percent), previous.disk_usage_percent
            ),
            disk_read_mb=self._io_value("read_bytes", previous.disk_read_mb),
            disk_write_mb=self._io_value("write_bytes", previous.disk_write_mb),
            network_rx_mb=self._net_value("bytes_recv", previous.network_rx_mb),
            network_tx_mb=self._net_value("bytes_sent", previous.network_tx_mb),
            process_count=self._safe(lambda: len(self.provider.pids()), previous.process_count),
            api_latency_ms=fmean(self._latencies) if self._latencies else 0,
            api_requests=self._api_requests,
            api_errors=self._api_errors,
        )
        self._history.append(snapshot)
        return snapshot

    def latest(self) -> MetricsSnapshot:
        return (self._history[-1] if self._history else self.collect()).model_copy(deep=True)

    def recent(self, limit: int = 120) -> list[MetricsSnapshot]:
        if not self._history:
            self.collect()
        safe_limit = max(1, min(limit, len(self._history)))
        return [snapshot.model_copy(deep=True) for snapshot in list(self._history)[-safe_limit:]]

    def record_request(self, latency_ms: float) -> None:
        self._api_requests += 1
        self._latencies.append(max(0, latency_ms))

    def record_error(self) -> None:
        self._api_errors += 1

    async def sampler(self, interval_seconds: float = 1.0) -> None:
        while True:
            self.collect()
            await asyncio.sleep(interval_seconds)

    def _io_value(self, name: str, fallback: float) -> float:
        return self._safe(
            lambda: float(getattr(self.provider.disk_io_counters(), name)) / 1024 / 1024,
            fallback,
        )

    def _net_value(self, name: str, fallback: float) -> float:
        return self._safe(
            lambda: float(getattr(self.provider.net_io_counters(), name)) / 1024 / 1024,
            fallback,
        )

    def _memory_values(self, previous: MetricsSnapshot) -> tuple[float, float]:
        current = self._read_cgroup_int(("memory.current", "memory.usage_in_bytes"))
        maximum = self._read_cgroup_int(("memory.max", "memory.limit_in_bytes"))
        if current is not None and maximum is not None and maximum > 0 and maximum < 2**60:
            return current / maximum * 100, max(0, maximum - current) / 1024 / 1024
        return (
            self._safe(lambda: float(self.provider.virtual_memory().percent), previous.memory_percent),
            self._safe(
                lambda: float(self.provider.virtual_memory().available) / 1024 / 1024,
                previous.memory_available_mb,
            ),
        )

    def _container_cpu_percent(self, fallback: float) -> float:
        quota_text = self._read_cgroup_text("cpu.max")
        stat_text = self._read_cgroup_text("cpu.stat")
        if quota_text and stat_text:
            quota, period = quota_text.split()[:2]
            if quota != "max":
                usage_line = next((line for line in stat_text.splitlines() if line.startswith("usage_usec ")), "")
                if usage_line:
                    usage = int(usage_line.split()[1])
                    now = time.monotonic()
                    if self._cgroup_cpu_previous is not None:
                        previous_usage, previous_time = self._cgroup_cpu_previous
                        elapsed = max(now - previous_time, 0.001)
                        quota_cores = max(float(quota) / float(period), 0.001)
                        percent = (usage - previous_usage) / 1_000_000 / elapsed / quota_cores * 100
                        self._cgroup_cpu_previous = (usage, now)
                        return max(0, min(percent, quota_cores * 100))
                    self._cgroup_cpu_previous = (usage, now)
        return self._safe(lambda: float(self.provider.cpu_percent(interval=None)), fallback)

    def _read_cgroup_text(self, name: str) -> str | None:
        try:
            with open(os.path.join(self.cgroup_root, name), encoding="utf-8") as handle:
                return handle.read().strip()
        except (OSError, UnicodeError):
            return None

    def _read_cgroup_int(self, names: tuple[str, ...]) -> int | None:
        for name in names:
            value = self._read_cgroup_text(name)
            if value and value != "max":
                try:
                    return int(value)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _safe(reader: Callable[[], Any], fallback: Any) -> Any:
        try:
            value = reader()
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError, psutil.Error):
            return fallback
        return fallback if value is None else value

