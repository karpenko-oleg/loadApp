import asyncio

from ..models import LoadProfile


def record_progress(metrics, kind: str, amount: float = 1) -> None:
    if metrics is not None and hasattr(metrics, "record_load_progress"):
        metrics.record_load_progress(kind, amount)


async def wait_for_stop(stop_event: asyncio.Event, timeout: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=max(0, timeout))
    except asyncio.TimeoutError:
        return


async def run_profile(profile: LoadProfile, stop_event: asyncio.Event, metrics=None) -> None:
    if profile.kind.value == "cpu":
        from . import cpu

        await cpu.run(profile, stop_event, metrics)
    elif profile.kind.value == "memory":
        from . import memory

        await memory.run(profile, stop_event, metrics)
    elif profile.kind.value == "disk":
        from . import disk

        await disk.run(profile, stop_event, metrics)
    else:
        from . import http

        await http.run(profile, stop_event, metrics)

