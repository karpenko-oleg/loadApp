import asyncio
import importlib

import httpx
import pytest


class Recorder:
    def __init__(self):
        self.events = []

    def record_load_progress(self, kind, amount=1):
        self.events.append((kind, amount))


def profile(kind, **overrides):
    data = {"kind": kind, "duration_seconds": 1, "intensity": 0.1}
    data.update(overrides)
    return importlib.import_module("app.models").LoadProfile(**data)


@pytest.mark.asyncio
async def test_cpu_loader_starts_bounded_worker_and_stops():
    loader = importlib.import_module("app.loaders.cpu")
    stop_event = asyncio.Event()
    recorder = Recorder()
    task = asyncio.create_task(loader.run(profile("cpu", workers=1), stop_event, recorder))

    await asyncio.sleep(0.1)
    stop_event.set()
    await task

    assert any(kind == "cpu" for kind, _ in recorder.events)


@pytest.mark.asyncio
async def test_memory_loader_releases_allocated_memory_on_stop():
    loader = importlib.import_module("app.loaders.memory")
    stop_event = asyncio.Event()
    recorder = Recorder()
    task = asyncio.create_task(loader.run(profile("memory", memory_mb=1), stop_event, recorder))

    await asyncio.sleep(0.05)
    stop_event.set()
    await task

    assert any(kind == "memory" for kind, _ in recorder.events)


@pytest.mark.asyncio
async def test_disk_loader_cleans_temporary_files(monkeypatch, tmp_path):
    loader = importlib.import_module("app.loaders.disk")
    monkeypatch.setattr(loader, "TEMP_ROOT", str(tmp_path))
    stop_event = asyncio.Event()
    recorder = Recorder()

    await loader.run(profile("disk", disk_mb=1), stop_event, recorder)

    assert list(tmp_path.iterdir()) == []
    assert any(kind == "disk" for kind, _ in recorder.events)


@pytest.mark.asyncio
async def test_http_loader_uses_bounded_concurrency_and_counts_requests():
    loader = importlib.import_module("app.loaders.http")
    requests = 0

    async def handler(request):
        nonlocal requests
        requests += 1
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    stop_event = asyncio.Event()
    recorder = Recorder()

    await loader.run(profile("http", concurrency=3), stop_event, recorder, client=client)
    await client.aclose()

    assert requests > 0
    assert any(kind == "http" for kind, _ in recorder.events)

