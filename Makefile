.PHONY: install dev test lint migrate smoke-esp-template

install:
	pip install -e ".[dev]"

dev:
	uvicorn email_platform.main:app --reload

test:
	pytest

lint:
	ruff check . && mypy src

migrate:
	alembic upgrade head

smoke-esp-template:
	node scripts/esp_template_smoke.mjs $${ESP_BASE_URL:-https://email-engine.app}
