# VPS Troubleshooting Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать учебное React + FastAPI приложение, которое показывает системные метрики VPS/контейнера, запускает безопасную искусственную нагрузку и позволяет тренировать диагностику отказов.

**Architecture:** Два сервиса в Docker Compose: FastAPI backend с sampler'ом, кольцевым буфером метрик, load jobs и fault state; Vite/React frontend с polling раз в 2 секунды, графиками и панелями управления. Nginx во frontend-контейнере проксирует `/api` и `/metrics` на backend.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Pydantic Settings, psutil, pytest/httpx; React 18, TypeScript, Vite, Recharts, Vitest, Testing Library; Docker Compose, Nginx.

**Spec:** `docs/superpowers/specs/2026-11-23-vps-troubleshooting-lab-design.md`

## Global Constraints

- Backend limits: duration ≤ 300 seconds, memory per job ≤ 512 MiB, disk per job ≤ 256 MiB, HTTP concurrency ≤ 50, CPU workers ≤ min(CPU count, 8).
- Backend must never execute shell commands from user input.
- Liveness `/api/healthz` remains available when readiness is degraded.
- Default metrics describe the application container; VPS mode is explicit and documented.
- No database, authentication, external DDoS/UDP flood or unrestricted resource exhaustion in v1.
- UI must visibly distinguish active, completed, failed, stale and offline states.
- Every behavior change is developed test-first: write a failing test, observe red, implement minimal code, observe green, then refactor.

## Review Focus

- Invalid or extreme job parameters are rejected consistently by API and UI; test in backend limits and frontend form tests.
- Jobs stop and clean up after cancellation, timeout and worker failure; test in load manager lifecycle tests.
- Sampler survives transient psutil errors and returns stable JSON shape; test collector fallback behavior.
- Faults do not hide liveness and do not accidentally persist across process restart; test health/fault routes.
- Frontend does not show fresh-looking data after API/network failure; test stale/offline rendering and polling cleanup.

---

### Task 1: Project skeleton and test harness

**Files:**
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/tests/__init__.py`
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`
- Create: `.gitignore`, `.env.example`
- Test: `backend/tests/test_imports.py`, `frontend/src/App.test.tsx`

**Interfaces:**
- Produces runnable Python and TypeScript test/build commands used by later tasks.

- [ ] **Step 1: Add the minimal project/config files and a placeholder test harness.**
- [ ] **Step 2: Write failing import/render tests for the backend package and frontend root component.**
- [ ] **Step 3: Run `cd backend && pytest -q` and `cd frontend && npm test -- --run`; confirm failures identify missing application behavior.**
- [ ] **Step 4: Add only the minimal package/root component needed to make the harness pass.**
- [ ] **Step 5: Run both test commands and the empty frontend build; confirm green baseline.**

### Task 2: Backend limits, models and load-job lifecycle

**Files:**
- Create: `backend/app/config.py`, `backend/app/models.py`, `backend/app/load_manager.py`
- Test: `backend/tests/test_models.py`, `backend/tests/test_load_manager.py`

**Interfaces:**
- Produces `LoadProfile`, `LoadJob`, `FaultState`, `MetricsSnapshot`, `LoadManager.start(profile)`, `LoadManager.stop(job_id)`, `LoadManager.list()`.
- `LoadProfile` accepts `kind` in `cpu|memory|disk|http`, `duration_seconds`, `intensity`, `workers`, `memory_mb`, `disk_mb`, `concurrency` and rejects values outside global limits.

- [ ] **Step 1: Write tests for valid profile normalization and rejection of duration, memory, disk, workers and concurrency over limits.**
- [ ] **Step 2: Run `pytest backend/tests/test_models.py -q`; observe the expected red failures.**
- [ ] **Step 3: Implement immutable Pydantic models and centralized `Settings`/limit constants.**
- [ ] **Step 4: Write lifecycle tests proving a job transitions `queued → running → completed`, cancellation becomes `stopped`, and unknown IDs return a controlled error.**
- [ ] **Step 5: Run the lifecycle tests to observe red, then implement `LoadManager` with bounded async task/process cleanup and automatic duration expiry.**
- [ ] **Step 6: Run `pytest backend/tests/test_models.py backend/tests/test_load_manager.py -q`; confirm all pass and no job survives fixture cleanup.**

### Task 3: Metrics sampler, faults and HTTP API

**Files:**
- Create: `backend/app/metrics.py`, `backend/app/faults.py`, `backend/app/prometheus.py`, `backend/app/main.py`
- Test: `backend/tests/test_metrics.py`, `backend/tests/test_faults.py`, `backend/tests/test_api.py`

**Interfaces:**
- `MetricsStore.latest()` and `MetricsStore.recent(limit)` return stable snapshots with timestamp, CPU, load, memory, disk, network, process and API counters.
- `FaultController.get()`/`update(patch)` owns delay, error rate and readiness degradation.
- API routes: `GET /api/healthz`, `GET /api/readiness`, `GET /api/metrics`, `GET /api/load/jobs`, `POST /api/load/jobs`, `DELETE /api/load/jobs/{job_id}`, `GET/PATCH /api/faults`, `GET /metrics`.

- [ ] **Step 1: Write collector tests with a fake psutil provider, including a transient provider exception and stable fallback values.**
- [ ] **Step 2: Run the collector tests and confirm red before implementing the sampler/store.**
- [ ] **Step 3: Implement the one-second sampler, bounded ten-minute ring buffer, API timing/error counters and snapshot serialization.**
- [ ] **Step 4: Write fault and health API tests proving delay/errors affect normal API calls, readiness can degrade, and liveness remains HTTP 200.**
- [ ] **Step 5: Run those tests to confirm red, then implement fault controller, FastAPI lifespan, CORS, error mapping and route handlers.**
- [ ] **Step 6: Write a Prometheus-format assertion for key gauges/counters, run the complete backend suite, and confirm green.**

### Task 4: Real bounded load profiles

**Files:**
- Create: `backend/app/loaders/cpu.py`, `backend/app/loaders/memory.py`, `backend/app/loaders/disk.py`, `backend/app/loaders/http.py`, `backend/app/loaders/__init__.py`
- Modify: `backend/app/load_manager.py`
- Test: `backend/tests/test_loaders.py`

**Interfaces:**
- Each loader exposes `async run(profile, stop_event, metrics) -> None` and honors cancellation, duration and its profile limits.
- CPU uses bounded worker processes; memory allocates bounded bytearrays and releases them; disk writes only under a configured temporary directory and removes files in `finally`; HTTP targets an internal loopback health endpoint with bounded concurrency.

- [ ] **Step 1: Write tests for each loader using short durations and tiny limits, asserting it starts, records progress and releases resources.**
- [ ] **Step 2: Run `pytest backend/tests/test_loaders.py -q` and verify red.**
- [ ] **Step 3: Implement the minimal CPU, memory, disk and internal HTTP loaders with cooperative cancellation and cleanup.**
- [ ] **Step 4: Run the loader tests and the complete backend suite; confirm green and inspect temporary directory cleanup.**
- [ ] **Step 5: Add an integration test that starts two compatible jobs, rejects a third request beyond aggregate limits, then stops both jobs cleanly.**

### Task 5: Frontend API client, dashboard and controls

**Files:**
- Create: `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/hooks/useLabData.ts`, `frontend/src/components/StatusCards.tsx`, `frontend/src/components/MetricsChart.tsx`, `frontend/src/components/LoadPanel.tsx`, `frontend/src/components/FaultPanel.tsx`, `frontend/src/components/EventTimeline.tsx`, `frontend/src/styles.css`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`
- Test: `frontend/src/App.test.tsx`, `frontend/src/hooks/useLabData.test.ts`

**Interfaces:**
- `api.getMetrics()`, `api.getJobs()`, `api.startJob(profile)`, `api.stopJob(id)`, `api.getFaults()`, `api.updateFaults(patch)`.
- `useLabData()` returns `{snapshot, history, jobs, faults, events, connectionState, startJob, stopJob, updateFaults}`.

- [ ] **Step 1: Write client tests for rejected form values, API error normalization and `stale/offline` state after polling failure.**
- [ ] **Step 2: Run `cd frontend && npm test -- --run`; confirm red.**
- [ ] **Step 3: Implement typed API client and polling hook with abort/cleanup, stale threshold and event timeline.**
- [ ] **Step 4: Write component tests for status cards, chart empty state, active job stop action and fault toggle controls.**
- [ ] **Step 5: Implement dashboard layout with dark high-contrast styling, responsive grid, accessible labels and explicit warning copy for resource loads.**
- [ ] **Step 6: Run frontend tests and `npm run build`; confirm green and no TypeScript errors.**

### Task 6: Docker Compose, reverse proxy and operations documentation

**Files:**
- Create: `backend/Dockerfile`, `backend/app/__main__.py`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `README.md`, `docs/troubleshooting-checklist.md`
- Modify: `.env.example`, `backend/pyproject.toml`, `frontend/package.json`
- Test: `backend/tests/test_smoke.py`

**Interfaces:**
- `docker compose up --build` exposes the dashboard on port 8080 and routes `/api` plus `/metrics` to backend.
- Backend container has a healthcheck against `/api/healthz`; frontend waits for backend health.

- [ ] **Step 1: Write the smoke test for healthz/readiness and the documented compose port contract.**
- [ ] **Step 2: Run the smoke test before Docker files exist and record the expected red/blocked result.**
- [ ] **Step 3: Implement Dockerfiles, Nginx proxy, compose healthchecks, environment defaults and safe resource limits.**
- [ ] **Step 4: Write README instructions for local start, VPS deployment behind firewall/VPN, container-vs-host metrics, safe load limits, curl examples and shutdown.**
- [ ] **Step 5: Add troubleshooting checklist covering CPU saturation, memory pressure, disk I/O, HTTP errors, readiness degradation, logs and recovery.**
- [ ] **Step 6: Run `docker compose config`, backend tests, frontend tests/build and a compose smoke check if Docker is available; document any environment limitation.**

### Task 7: Final verification and handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-11-23-vps-troubleshooting-lab-design.md`, `docs/superpowers/plans/2026-11-23-vps-troubleshooting-lab-plan.md` only if implementation decisions diverge.

- [ ] **Step 1: Run the full backend suite with `cd backend && pytest -q`.**
- [ ] **Step 2: Run the full frontend suite with `cd frontend && npm test -- --run` and `npm run build`.**
- [ ] **Step 3: Run `docker compose config` and, when available, `docker compose up --build -d`, health-check the dashboard, then stop it with `docker compose down`.**
- [ ] **Step 4: Manually verify one CPU job, one disk/memory job, one fault toggle, recovery and `/metrics` output.**
- [ ] **Step 5: Review the diff/file tree and report exact commands, test counts, limitations and the first suggested VPS lab exercise.**
