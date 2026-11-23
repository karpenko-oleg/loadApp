import importlib
from types import SimpleNamespace

import psutil


class FakePsutil:
    def __init__(self):
        self.fail_cpu_once = False

    def cpu_percent(self, interval=None):
        if self.fail_cpu_once:
            self.fail_cpu_once = False
            raise RuntimeError("temporary psutil failure")
        return 42.5

    def getloadavg(self):
        return (1.25, 0.9, 0.7)

    def virtual_memory(self):
        return SimpleNamespace(percent=61.0, available=256 * 1024 * 1024)

    def disk_usage(self, path):
        return SimpleNamespace(percent=73.0)

    def disk_io_counters(self):
        return SimpleNamespace(read_bytes=12 * 1024 * 1024, write_bytes=8 * 1024 * 1024)

    def net_io_counters(self):
        return SimpleNamespace(bytes_recv=20 * 1024 * 1024, bytes_sent=5 * 1024 * 1024)

    def pids(self):
        return [1, 2, 3]


def test_metrics_store_collects_stable_snapshot_and_survives_provider_error():
    metrics = importlib.import_module("app.metrics")
    provider = FakePsutil()
    store = metrics.MetricsStore(provider=provider, history_size=3)

    first = store.collect()
    assert first.cpu_percent == 42.5
    assert first.load_1m == 1.25
    assert first.memory_available_mb == 256
    assert first.process_count == 3

    provider.fail_cpu_once = True
    fallback = store.collect()
    assert fallback.cpu_percent == first.cpu_percent
    assert len(store.recent(10)) == 2


def test_metrics_store_tracks_api_counters():
    metrics = importlib.import_module("app.metrics")
    store = metrics.MetricsStore(provider=FakePsutil())

    store.record_request(12.5)
    store.record_request(7.5)
    store.record_error()
    snapshot = store.collect()

    assert snapshot.api_requests == 2
    assert snapshot.api_errors == 1
    assert snapshot.api_latency_ms == 10


def test_metrics_store_survives_psutil_error_and_recovers_on_next_sample():
    metrics = importlib.import_module("app.metrics")
    provider = FakePsutil()
    store = metrics.MetricsStore(provider=provider)
    store.collect()

    def denied_cpu(interval=None):
        raise psutil.AccessDenied(pid=1)

    provider.cpu_percent = denied_cpu
    denied = store.collect()
    provider.cpu_percent = lambda interval=None: 55.0
    recovered = store.collect()

    assert denied.cpu_percent == 42.5
    assert recovered.cpu_percent == 55.0
    assert set(denied.model_dump()) == set(recovered.model_dump())


def test_metrics_store_prefers_container_memory_cgroup_when_available(tmp_path):
    metrics = importlib.import_module("app.metrics")
    (tmp_path / "memory.current").write_text(str(256 * 1024 * 1024))
    (tmp_path / "memory.max").write_text(str(1024 * 1024 * 1024))
    store = metrics.MetricsStore(provider=FakePsutil(), cgroup_root=str(tmp_path))

    snapshot = store.collect()

    assert snapshot.memory_percent == 25
    assert snapshot.memory_available_mb == 768

