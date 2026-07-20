import importlib

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import allowed_origins, app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_reads_frontend_origin_from_environment(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://fragility.vercel.app")

    assert Settings().frontend_origin == "https://fragility.vercel.app"


def test_allowed_origins_normalizes_the_configured_origin():
    assert allowed_origins("http://localhost:3000") == ["http://localhost:3000"]
    assert allowed_origins("https://fragility.vercel.app/") == [
        "http://localhost:3000",
        "https://fragility.vercel.app",
    ]
    assert "*" not in allowed_origins("https://fragility.vercel.app")


def test_preflight_allows_the_configured_production_origin(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://fragility.vercel.app/")
    import app.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    production_app = importlib.reload(main_module).app

    try:
        client = TestClient(production_app)
        response = client.options(
            "/health",
            headers={
                "Origin": "https://fragility.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://fragility.vercel.app"
    finally:
        monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:3000")
        importlib.reload(config_module)
        importlib.reload(main_module)
