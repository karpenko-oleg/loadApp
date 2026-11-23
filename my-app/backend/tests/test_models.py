import importlib

import pytest
from pydantic import ValidationError


def profile_model():
    return importlib.import_module("app.models").LoadProfile


def test_load_profile_applies_safe_defaults():
    profile = profile_model()(kind="cpu", duration_seconds=5)

    assert profile.duration_seconds == 5
    assert profile.intensity == 0.5
    assert profile.workers == 1
    assert profile.memory_mb == 64
    assert profile.disk_mb == 16
    assert profile.concurrency == 4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_seconds", 301),
        ("memory_mb", 513),
        ("disk_mb", 257),
        ("workers", 9),
        ("concurrency", 51),
    ],
)
def test_load_profile_rejects_values_above_safety_limits(field, value):
    payload = {"kind": "cpu", "duration_seconds": 5}
    payload[field] = value

    with pytest.raises(ValidationError):
        profile_model()(**payload)


def test_load_profile_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        profile_model()(kind="fork-bomb", duration_seconds=5)

