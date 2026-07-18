.PHONY: install test lint refresh api

install:
	python -m pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check src tests

refresh:
	fragility-map refresh

api:
	uvicorn fragility_map.api.server:app --reload
