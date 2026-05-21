from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from email_platform.api.routes import router
from email_platform.core.settings import get_settings
from email_platform.db.session import SessionLocal

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.environment}


@app.get('/ready')
def ready() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ready'}


app.include_router(router)
