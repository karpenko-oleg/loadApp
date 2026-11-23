from datetime import datetime, timezone
from enum import Enum
import os
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import LIMITS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LoadKind(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    HTTP = "http"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class LoadProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: LoadKind
    duration_seconds: float = Field(default=30, ge=1, le=LIMITS.max_duration_seconds)
    intensity: float = Field(default=0.5, ge=0, le=1)
    workers: int = Field(default=1, ge=1, le=LIMITS.max_cpu_workers)
    memory_mb: int = Field(default=64, ge=1, le=LIMITS.max_memory_mb)
    disk_mb: int = Field(default=16, ge=1, le=LIMITS.max_disk_mb)
    concurrency: int = Field(default=4, ge=1, le=LIMITS.max_concurrency)

    @field_validator("workers")
    @classmethod
    def workers_fit_cpu_count(cls, value: int) -> int:
        max_workers = min(LIMITS.max_cpu_workers, max(1, os.cpu_count() or 1))
        if value > max_workers:
            raise ValueError(f"Количество процессов не может превышать {max_workers} на этом хосте")
        return value


class LoadJob(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    profile: LoadProfile
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class FaultState(BaseModel):
    api_delay_ms: int = Field(default=0, ge=0, le=5000)
    error_rate: float = Field(default=0, ge=0, le=1)
    readiness_degraded: bool = False


class MetricsSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    cpu_percent: float = 0
    load_1m: float = 0
    memory_percent: float = 0
    memory_available_mb: float = 0
    disk_usage_percent: float = 0
    disk_read_mb: float = 0
    disk_write_mb: float = 0
    network_rx_mb: float = 0
    network_tx_mb: float = 0
    process_count: int = 0
    api_latency_ms: float = 0
    api_requests: int = 0
    api_errors: int = 0

