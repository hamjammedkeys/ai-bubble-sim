import json
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_render_blueprint_defines_backend_service_without_secret_values():
    blueprint = yaml.safe_load(
        (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")
    )

    assert len(blueprint["services"]) == 1
    service = blueprint["services"][0]
    assert service["type"] == "web"
    assert service["name"] == "fragilitygraph-api"
    assert service["runtime"] == "python"
    assert service["rootDir"] == "revamp/backend"
    assert service["buildCommand"] == "uv sync --frozen"
    assert service["startCommand"] == (
        "uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    )
    assert service["healthCheckPath"] == "/health"

    env_vars = {variable["key"]: variable for variable in service["envVars"]}
    for secret_name in ("DATABASE_URL", "FRONTEND_ORIGIN", "OPENAI_API_KEY"):
        assert env_vars[secret_name]["sync"] is False
        assert "value" not in env_vars[secret_name]


def test_vercel_config_selects_nextjs_framework():
    config = json.loads(
        (REPOSITORY_ROOT / "revamp/frontend/vercel.json").read_text(
            encoding="utf-8"
        )
    )

    assert config["framework"] == "nextjs"
