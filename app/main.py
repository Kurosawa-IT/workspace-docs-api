from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.workspaces import router as workspaces_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(auth_router)

app.include_router(workspaces_router)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}
