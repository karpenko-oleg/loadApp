import asyncio
import os
import time

import httpx

from ..models import LoadProfile
from . import record_progress


TARGET_URL = os.getenv("LOAD_HTTP_TARGET", "http://127.0.0.1:8000/api/healthz")


async def run(profile: LoadProfile, stop_event: asyncio.Event, metrics=None, client=None) -> None:
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=2)
    deadline = time.monotonic() + profile.duration_seconds
    semaphore = asyncio.Semaphore(profile.concurrency)

    async def request_once() -> None:
        async with semaphore:
            try:
                response = await client.get(TARGET_URL)
                record_progress(metrics, "http", 1 if response.status_code < 500 else 0)
            except httpx.HTTPError:
                record_progress(metrics, "http", 0)

    try:
        while not stop_event.is_set() and time.monotonic() < deadline:
            await asyncio.gather(*(request_once() for _ in range(profile.concurrency)))
    finally:
        if own_client:
            await client.aclose()

