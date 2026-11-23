import time

from fastapi.testclient import TestClient

from app.main import app, metrics_store


def test_health_readiness_and_faults_are_exposed():
    with TestClient(app) as client:
        assert client.get("/api/healthz").status_code == 200
        assert client.get("/api/readiness").status_code == 200

        response = client.patch(
            "/api/faults",
            json={"readiness_degraded": True, "error_rate": 1, "api_delay_ms": 20},
        )
        assert response.status_code == 200

        started = time.perf_counter()
        assert client.get("/api/metrics").status_code == 503
        assert time.perf_counter() - started >= 0.015
        assert client.get("/api/readiness").status_code == 503
        assert client.get("/api/healthz").status_code == 200

        client.patch(
            "/api/faults",
            json={"readiness_degraded": False, "error_rate": 0, "api_delay_ms": 0},
        )


def test_load_job_routes_start_list_and_stop_a_job():
    with TestClient(app) as client:
        response = client.post(
            "/api/load/jobs",
            json={"kind": "cpu", "duration_seconds": 5, "workers": 1},
        )
        assert response.status_code == 201
        job_id = response.json()["id"]
        assert any(job["id"] == job_id for job in client.get("/api/load/jobs").json())

        stopped = client.delete(f"/api/load/jobs/{job_id}")
        assert stopped.status_code == 200
        assert stopped.json()["status"] == "stopped"


def test_prometheus_endpoint_contains_core_metrics():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "vps_lab_cpu_percent" in response.text
    assert "vps_lab_api_requests_total" in response.text


def test_injected_http_error_increments_error_counter_once():
    with TestClient(app) as client:
        before = metrics_store._api_errors
        client.patch("/api/faults", json={"error_rate": 1})
        assert client.get("/api/load/jobs").status_code == 503
        client.patch("/api/faults", json={"error_rate": 0})

    assert metrics_store._api_errors - before == 1

