import asyncio
import importlib

import pytest


def models():
    return importlib.import_module("app.models")


def load_manager():
    return importlib.import_module("app.load_manager").LoadManager


@pytest.mark.asyncio
async def test_job_moves_from_queued_to_running_to_completed():
    started = asyncio.Event()

    async def runner(profile, stop_event):
        started.set()
        await asyncio.sleep(0.01)

    manager = load_manager()(runner=runner)
    job = await manager.start(models().LoadProfile(kind="cpu", duration_seconds=5))

    await started.wait()
    await manager.wait(job.id)

    assert manager.get(job.id).status == "completed"


@pytest.mark.asyncio
async def test_stop_marks_running_job_stopped_and_unknown_id_is_controlled():
    release = asyncio.Event()

    async def runner(profile, stop_event):
        await stop_event.wait()
        await release.wait()

    manager = load_manager()(runner=runner)
    job = await manager.start(models().LoadProfile(kind="cpu", duration_seconds=30))

    stopped = await manager.stop(job.id)

    assert stopped.status == "stopped"
    with pytest.raises(KeyError):
        await manager.stop("missing-job")


@pytest.mark.asyncio
async def test_aggregate_active_job_limit_rejects_third_job_and_allows_cleanup():
    async def runner(profile, stop_event):
        await stop_event.wait()

    manager = load_manager()(runner=runner)
    first = await manager.start(models().LoadProfile(kind="cpu", duration_seconds=30))
    second = await manager.start(models().LoadProfile(kind="memory", duration_seconds=30))

    try:
        with pytest.raises(RuntimeError, match="активных заданий"):
            await manager.start(models().LoadProfile(kind="disk", duration_seconds=30))
    finally:
        assert (await manager.stop(first.id)).status == "stopped"
        assert (await manager.stop(second.id)).status == "stopped"


@pytest.mark.asyncio
async def test_memory_budget_rejects_combined_jobs_and_releases_after_stop():
    async def runner(profile, stop_event):
        await stop_event.wait()

    manager = load_manager()(runner=runner)
    first = await manager.start(models().LoadProfile(kind="memory", duration_seconds=30, memory_mb=256))

    with pytest.raises(RuntimeError, match="Лимит памяти"):
        await manager.start(models().LoadProfile(kind="memory", duration_seconds=30, memory_mb=256))

    await manager.stop(first.id)
    second = await manager.start(models().LoadProfile(kind="memory", duration_seconds=30, memory_mb=256))
    assert second.status == "running"
    await manager.stop(second.id)


@pytest.mark.asyncio
async def test_hung_runner_hits_deadline_and_shutdown_stops_active_jobs():
    async def hung_runner(profile, stop_event):
        await asyncio.Event().wait()

    manager = load_manager()(runner=hung_runner)
    job = await manager.start(models().LoadProfile(kind="cpu", duration_seconds=1))
    finished = await manager.wait(job.id)

    assert finished.status == "failed"
    assert finished.error == "Задание превысило установленный срок"

    active = await manager.start(models().LoadProfile(kind="cpu", duration_seconds=30))
    await manager.shutdown()
    assert manager.get(active.id).status == "stopped"

