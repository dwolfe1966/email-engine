FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "email_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
