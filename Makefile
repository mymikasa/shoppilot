.PHONY: install ingest dev test lint fmt up down clean

install:
	uv sync --extra dev

ingest:
	uv run python -m scripts.ingest_faq

dev:
	uv run uvicorn shoppilot.main:app --reload --port 8000

test:
	uv run pytest

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

up:
	docker compose up -d

down:
	docker compose down

clean:
	rm -rf data/chroma .pytest_cache .ruff_cache
