from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Limits:
    max_duration_seconds: int = 300
    max_memory_mb: int = 512
    max_disk_mb: int = 256
    max_concurrency: int = 50
    max_cpu_workers: int = 8
    max_active_jobs: int = 2
    max_memory_budget_mb: int = 384
    max_completed_jobs: int = 50
    job_grace_seconds: float = 0.25


LIMITS = Limits()
CPU_COUNT = max(1, os.cpu_count() or 1)

