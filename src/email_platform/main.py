from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from email_platform.api.admin_console import router as admin_console_router
from email_platform.api.auth import router as auth_router
from email_platform.api.compat import router as compat_router
from email_platform.api.routes import router
from email_platform.api.template_editor import router as template_editor_router
from email_platform.api.test_console import router as test_console_router
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


@app.get('/', include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse('/admin', status_code=307)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.environment}


@app.get('/ready')
def ready() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ready'}


app.include_router(auth_router)
app.include_router(router)
app.include_router(compat_router)
app.include_router(admin_console_router)
app.include_router(test_console_router)
app.include_router(template_editor_router)
