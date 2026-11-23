import asyncio

from ..models import LoadProfile
from . import record_progress, wait_for_stop


async def run(profile: LoadProfile, stop_event: asyncio.Event, metrics=None) -> None:
    buffer = bytearray(profile.memory_mb * 1024 * 1024)
    try:
        for index in range(0, len(buffer), 4096):
            buffer[index] = index % 251
        elapsed = 0.0
        while not stop_event.is_set() and elapsed < profile.duration_seconds:
            record_progress(metrics, "memory", profile.memory_mb)
            await wait_for_stop(stop_event, 0.25)
            elapsed += 0.25
    finally:
        buffer.clear()
        del buffer

