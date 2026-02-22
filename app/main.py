import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.workspaces import router as workspaces_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.request_id import request_id_var

app = FastAPI(title=settings.app_name)

configure_logging()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id")
        rid = incoming if incoming else str(uuid.uuid4())

        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = rid
        return response


app.add_middleware(RequestIdMiddleware)

app.include_router(auth_router)

app.include_router(workspaces_router)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}
