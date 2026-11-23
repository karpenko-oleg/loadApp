import importlib

import pytest
from pydantic import ValidationError


def test_fault_controller_roundtrip_and_rejects_unsafe_values():
    faults = importlib.import_module("app.faults")
    controller = faults.FaultController()

    updated = controller.update({"api_delay_ms": 120, "error_rate": 0.25, "readiness_degraded": True})

    assert updated.api_delay_ms == 120
    assert updated.error_rate == 0.25
    assert updated.readiness_degraded is True
    with pytest.raises(ValidationError):
        controller.update({"api_delay_ms": 99999})

