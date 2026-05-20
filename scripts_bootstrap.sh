#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
cp -n .env.example .env || true
docker compose up -d postgres
alembic upgrade head
uvicorn email_platform.main:app --reload
