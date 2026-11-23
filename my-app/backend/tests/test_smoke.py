from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


def test_compose_exposes_dashboard_and_waits_for_backend_health():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]

    assert services["frontend"]["ports"][0] in {
        "127.0.0.1:8080:80",
        "${FRONTEND_BIND:-127.0.0.1}:${FRONTEND_PORT:-8080}:80",
    }
    assert services["frontend"]["depends_on"]["backend"]["condition"] == "service_healthy"
    assert "/api/healthz" in " ".join(services["backend"]["healthcheck"]["test"])

