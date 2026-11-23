import asyncio
import os
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .faults import FaultController
from .load_manager import LoadManager
from .metrics import MetricsStore
from .models import FaultState, LoadProfile
from .prometheus import render_prometheus


metrics_store = MetricsStore(
    history_size=int(os.getenv("METRICS_HISTORY_SECONDS", "600")),
    sample_interval=float(os.getenv("METRICS_SAMPLE_INTERVAL", "1.0")),
)
fault_controller = FaultController()
load_manager = LoadManager(metrics=metrics_store)


@asynccontextmanager
async def lifespan(application: FastAPI):
    metrics_store.collect()
    sampler = asyncio.create_task(metrics_store.sampler(metrics_store.sample_interval))
    try:
        yield
    finally:
        await load_manager.shutdown()
        sampler.cancel()
        try:
            await sampler
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Лаборатория диагностики VPS", lifespan=lifespan)
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def apply_faults() -> None:
    faults = fault_controller.get()
    if faults.api_delay_ms:
        await asyncio.sleep(faults.api_delay_ms / 1000)
    if faults.error_rate and random.random() < faults.error_rate:
        raise HTTPException(status_code=503, detail="Искусственная ошибка API")


@app.middleware("http")
async def record_api_metrics(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    metrics_store.record_request((time.perf_counter() - started) * 1000)
    if response.status_code >= 500:
        metrics_store.record_error()
    return response


@app.get("/api/healthz")
async def healthz():
    return {"status": "ok", "service": "backend"}


@app.get("/api/readiness")
async def readiness():
    faults = fault_controller.get()
    if faults.readiness_degraded:
        return Response(
            content='{"status":"degraded","reason":"искусственный отказ"}',
            media_type="application/json",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return {"status": "ready"}


@app.get("/api/metrics")
async def metrics():
    await apply_faults()
    return {"latest": metrics_store.latest(), "history": metrics_store.recent(120)}


@app.get("/api/load/jobs")
async def list_jobs():
    await apply_faults()
    return load_manager.list()


@app.post("/api/load/jobs", status_code=status.HTTP_201_CREATED)
async def start_job(profile: LoadProfile):
    await apply_faults()
    try:
        return await load_manager.start(profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/api/load/jobs/{job_id}")
async def stop_job(job_id: str):
    try:
        return await load_manager.stop(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Задание не найдено") from exc


@app.get("/api/faults")
async def get_faults():
    return fault_controller.get()


@app.patch("/api/faults")
async def update_faults(patch: FaultState):
    return fault_controller.update(patch.model_dump(exclude_unset=True))


@app.get("/metrics")
async def prometheus_metrics():
    return Response(render_prometheus(metrics_store), media_type="text/plain")

