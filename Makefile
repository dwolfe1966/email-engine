.PHONY: install dev test lint migrate

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
