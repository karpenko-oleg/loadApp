import asyncio
import os
from pathlib import Path
import tempfile
import time

from ..models import LoadProfile
from . import record_progress, wait_for_stop


TEMP_ROOT = os.getenv("LOAD_TEMP_DIR", "/tmp/vps-lab")


def _write_disk(profile: LoadProfile, stop_event: asyncio.Event, metrics=None) -> None:
    Path(TEMP_ROOT).mkdir(parents=True, exist_ok=True)
    payload = b"vps-troubleshooting-lab\n" * (1024 * 1024 // len(b"vps-troubleshooting-lab\n"))
    with tempfile.TemporaryDirectory(prefix="disk-job-", dir=TEMP_ROOT) as job_dir:
        target = Path(job_dir) / "load.bin"
        with target.open("wb") as handle:
            for _ in range(profile.disk_mb):
                if stop_event.is_set():
                    break
                handle.write(payload)
                handle.flush()
                record_progress(metrics, "disk", len(payload))
            os.fsync(handle.fileno())


async def run(profile: LoadProfile, stop_event: asyncio.Event, metrics=None) -> None:
    deadline = time.monotonic() + profile.duration_seconds
    write_task = asyncio.create_task(asyncio.to_thread(_write_disk, profile, stop_event, metrics))
    try:
        await asyncio.shield(write_task)
    except asyncio.CancelledError:
        stop_event.set()
        await write_task
        raise
    await wait_for_stop(stop_event, max(0, deadline - time.monotonic()))

