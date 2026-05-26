from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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
ROOT_DIR = Path(__file__).resolve().parents[2]
ESP_DIST_DIR = ROOT_DIR / 'frontend' / 'dist'
ESP_INDEX = ESP_DIST_DIR / 'index.html'
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


if (ESP_DIST_DIR / 'assets').exists():
    app.mount('/esp/assets', StaticFiles(directory=ESP_DIST_DIR / 'assets'), name='esp-assets')


@app.get('/esp', include_in_schema=False)
def esp_app() -> FileResponse:
    if not ESP_INDEX.exists():
        raise HTTPException(status_code=503, detail='ESP frontend has not been built')
    return FileResponse(ESP_INDEX)


@app.get('/esp/{path:path}', include_in_schema=False)
def esp_app_fallback(path: str) -> FileResponse:
    if path.startswith('assets/'):
        raise HTTPException(status_code=404, detail='ESP asset not found')
    if not ESP_INDEX.exists():
        raise HTTPException(status_code=503, detail='ESP frontend has not been built')
    return FileResponse(ESP_INDEX)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.environment}


@app.get('/ready')
def ready() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ready'}


# Auth router mounted under two prefixes. /api/v1/auth/... is the
# native email-engine path; /api/auth/... is the alias the shared
# SentientMail UI calls. Both share one handler — the duplicate mount
# is a routing affordance only, not a duplicated implementation.
app.include_router(auth_router, prefix='/api/v1/auth')
app.include_router(auth_router, prefix='/api/auth')
app.include_router(router)
app.include_router(compat_router)
app.include_router(admin_console_router)
app.include_router(test_console_router)
app.include_router(template_editor_router)
