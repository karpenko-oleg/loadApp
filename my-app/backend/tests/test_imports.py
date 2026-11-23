import importlib


def test_backend_exposes_fastapi_application():
    module = importlib.import_module("app.main")

    assert module.app.title == "Лаборатория диагностики VPS"

