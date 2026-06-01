from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from email_platform.api.admin_console import router as admin_console_router
from email_platform.api.auth import router as auth_router, set_session_cookie
from email_platform.api.compat import router as compat_router
from email_platform.api.deps import (
    require_user,
    requires_operator_auth_path,
    user_from_session_token,
    visitor_method_allowed,
)
from email_platform.api.routes import router
from email_platform.api.template_editor import router as template_editor_router
from email_platform.api.test_console import router as test_console_router
from email_platform.core.settings import get_settings
from email_platform.db.session import SessionLocal
from email_platform.services.auth import SESSION_COOKIE_NAME, create_session
from email_platform.services.bootstrap import (
    bootstrap_operator_user,
    ensure_visitor_user,
    should_bootstrap_operator,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if should_bootstrap_operator(settings):
        with SessionLocal() as db:
            bootstrap_operator_user(db, settings)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
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


@app.middleware('http')
async def enforce_operator_api_auth(request: Request, call_next):
    operator_path = requires_operator_auth_path(request.url.path)
    if operator_path:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        user = None
        with SessionLocal() as db:
            user = user_from_session_token(db, token)
            if user is not None:
                db.commit()
        if settings.require_gui_auth and user is None:
            return JSONResponse(
                {'detail': 'Not authenticated'},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={'WWW-Authenticate': 'Cookie'},
            )
        if user is not None and user.role == 'visitor' and not visitor_method_allowed(
            request.method,
            request.url.path,
        ):
            return JSONResponse(
                {'detail': 'Visitor access is read-only'},
                status_code=status.HTTP_403_FORBIDDEN,
            )
    return await call_next(request)


@app.get('/', include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse('/admin', status_code=307)


if (ESP_DIST_DIR / 'assets').exists():
    app.mount('/esp/assets', StaticFiles(directory=ESP_DIST_DIR / 'assets'), name='esp-assets')


@app.get('/esp', include_in_schema=False)
def esp_app() -> FileResponse:
    if not ESP_INDEX.exists():
        raise HTTPException(status_code=503, detail='ESP frontend has not been built')
    return FileResponse(ESP_INDEX, headers={'Cache-Control': 'no-store'})


@app.get('/esp/visitor', include_in_schema=False)
def esp_visitor() -> RedirectResponse:
    if not settings.visitor_access_enabled:
        raise HTTPException(status_code=404, detail='Visitor access is not enabled')
    with SessionLocal() as db:
        visitor = ensure_visitor_user(db, settings)
        _row, raw_token = create_session(db, user=visitor)
        db.commit()
    response = RedirectResponse('/esp', status_code=303)
    set_session_cookie(response, raw_token)
    return response


@app.get('/esp/{path:path}', include_in_schema=False)
def esp_app_fallback(path: str) -> FileResponse:
    if path.startswith('assets/'):
        raise HTTPException(status_code=404, detail='ESP asset not found')
    if not ESP_INDEX.exists():
        raise HTTPException(status_code=503, detail='ESP frontend has not been built')
    return FileResponse(ESP_INDEX, headers={'Cache-Control': 'no-store'})


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
gui_dependencies = [Depends(require_user)] if settings.require_gui_auth else []
app.include_router(router)
app.include_router(compat_router, dependencies=gui_dependencies)
app.include_router(admin_console_router, dependencies=gui_dependencies)
app.include_router(test_console_router, dependencies=gui_dependencies)
app.include_router(template_editor_router, dependencies=gui_dependencies)
