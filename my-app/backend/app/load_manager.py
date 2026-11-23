import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

from .config import LIMITS
from .loaders import run_profile
from .models import JobStatus, LoadJob, LoadProfile, utc_now


Runner = Callable[[LoadProfile, asyncio.Event], Awaitable[None]]


class LoadManager:
    def __init__(self, runner: Runner | None = None, metrics=None):
        self._metrics = metrics
        self._runner = runner or self._default_runner
        self._jobs: dict[str, LoadJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._stop_events: dict[str, asyncio.Event] = {}
        self._reserved_memory_mb = 0
        self._memory_reservations: dict[str, int] = {}

    async def start(self, profile: LoadProfile) -> LoadJob:
        active = sum(
            job.status in {JobStatus.QUEUED, JobStatus.RUNNING}
            for job in self._jobs.values()
        )
        if active >= LIMITS.max_active_jobs:
            raise RuntimeError(f"Разрешено не более {LIMITS.max_active_jobs} активных заданий")
        if self._reserved_memory_mb + profile.memory_mb > LIMITS.max_memory_budget_mb:
            raise RuntimeError(f"Лимит памяти для заданий: {LIMITS.max_memory_budget_mb} МиБ")

        job = LoadJob(profile=profile)
        stop_event = asyncio.Event()
        self._jobs[job.id] = job
        self._stop_events[job.id] = stop_event
        self._memory_reservations[job.id] = profile.memory_mb
        self._reserved_memory_mb += profile.memory_mb
        self._tasks[job.id] = asyncio.create_task(self._run(job.id, profile, stop_event))
        await asyncio.sleep(0)
        return self.get(job.id)

    async def _run(self, job_id: str, profile: LoadProfile, stop_event: asyncio.Event) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = utc_now()
        try:
            await asyncio.wait_for(
                self._runner(profile, stop_event),
                timeout=profile.duration_seconds + LIMITS.job_grace_seconds,
            )
        except asyncio.TimeoutError:
            stop_event.set()
            job.status = JobStatus.FAILED
            job.error = "Задание превысило установленный срок"
        except asyncio.CancelledError:
            job.status = JobStatus.STOPPED
            raise
        except Exception as exc:  # noqa: BLE001 - job failures are observable state
            job.status = JobStatus.FAILED
            job.error = str(exc)
        else:
            job.status = JobStatus.COMPLETED if not stop_event.is_set() else JobStatus.STOPPED
        finally:
            job.finished_at = utc_now()
            self._reserved_memory_mb -= self._memory_reservations.pop(job_id, 0)
            self._prune_history()

    async def stop(self, job_id: str) -> LoadJob:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        job = self._jobs[job_id]
        if job.status in {JobStatus.COMPLETED, JobStatus.STOPPED, JobStatus.FAILED}:
            return self.get(job_id)
        self._stop_events[job_id].set()
        task = self._tasks[job_id]
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        job.status = JobStatus.STOPPED
        job.finished_at = job.finished_at or utc_now()
        return self.get(job_id)

    async def wait(self, job_id: str) -> LoadJob:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        await self._tasks[job_id]
        return self.get(job_id)

    def get(self, job_id: str) -> LoadJob:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        return self._jobs[job_id].model_copy(deep=True)

    def list(self) -> list[LoadJob]:
        return [job.model_copy(deep=True) for job in self._jobs.values()]

    async def shutdown(self) -> None:
        active_ids = [
            job.id
            for job in self._jobs.values()
            if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}
        ]
        await asyncio.gather(*(self.stop(job_id) for job_id in active_ids), return_exceptions=True)

    def _prune_history(self) -> None:
        completed = [
            job for job in self._jobs.values()
            if job.status in {JobStatus.COMPLETED, JobStatus.STOPPED, JobStatus.FAILED}
        ]
        overflow = len(completed) - LIMITS.max_completed_jobs
        if overflow <= 0:
            return
        for job in sorted(completed, key=lambda item: item.finished_at or datetime.min)[:overflow]:
            self._jobs.pop(job.id, None)
            self._tasks.pop(job.id, None)
            self._stop_events.pop(job.id, None)

    async def _default_runner(self, profile: LoadProfile, stop_event: asyncio.Event) -> None:
        await run_profile(profile, stop_event, self._metrics)

