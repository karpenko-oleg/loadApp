import asyncio
from concurrent.futures import ProcessPoolExecutor
import time

from ..models import LoadProfile
from . import record_progress


def _burn(seconds: float, intensity: float) -> int:
    end = time.monotonic() + seconds
    value = 0
    while time.monotonic() < end:
        for number in range(10_000):
            value = (value * 33 + number) % 1_000_003
        if intensity < 0.95:
            time.sleep((1 - intensity) * 0.002)
    return value


async def run(profile: LoadProfile, stop_event: asyncio.Event, metrics=None) -> None:
    loop = asyncio.get_running_loop()
    executor = ProcessPoolExecutor(max_workers=profile.workers)
    deadline = time.monotonic() + profile.duration_seconds
    try:
        while not stop_event.is_set() and time.monotonic() < deadline:
            chunk = min(0.2, max(0.01, deadline - time.monotonic()))
            futures = [
                loop.run_in_executor(executor, _burn, chunk, profile.intensity)
                for _ in range(profile.workers)
            ]
            await asyncio.gather(*futures)
            record_progress(metrics, "cpu", profile.workers)
    finally:
        shutdown = asyncio.create_task(
            asyncio.to_thread(executor.shutdown, wait=True, cancel_futures=True)
        )
        try:
            await asyncio.shield(shutdown)
        except asyncio.CancelledError:
            await shutdown
            raise

