from fastapi import FastAPI

from email_platform.api.routes import router
from email_platform.core.settings import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.environment}


app.include_router(router)
