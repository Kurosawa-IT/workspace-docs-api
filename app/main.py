import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.workspaces import router as workspaces_router
from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.log_context import (
    latency_ms_var,
    method_var,
    path_var,
    status_code_var,
    user_id_var,
    workspace_id_var,
)
from app.core.logging import init_logging
from app.core.request_id import request_id_var

app = FastAPI(title=settings.app_name)

install_exception_handlers(app)
init_logging()

req_logger = logging.getLogger("app.request")


@app.middleware("http")
async def request_context_and_log(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())

    t_rid = request_id_var.set(rid)
    t_path = path_var.set(request.url.path)
    t_method = method_var.set(request.method)
    t_status = status_code_var.set(None)
    t_lat = latency_ms_var.set(None)
    t_user = user_id_var.set(None)
    t_ws = workspace_id_var.set(None)

    start = time.perf_counter()
    try:
        response = await call_next(request)
        status_code_var.set(response.status_code)
        latency_ms_var.set(int((time.perf_counter() - start) * 1000))
        response.headers["X-Request-ID"] = rid
        user_id_var.set(getattr(request.state, "user_id", "-"))
        workspace_id_var.set(getattr(request.state, "workspace_id", "-"))
        req_logger.info("request", extra={"event": "http_request"})
        return response
    except Exception:
        status_code_var.set(500)
        latency_ms_var.set(int((time.perf_counter() - start) * 1000))
        user_id_var.set(getattr(request.state, "user_id", "-"))
        workspace_id_var.set(getattr(request.state, "workspace_id", "-"))
        req_logger.exception("request_failed", extra={"event": "http_request"})
        raise
    finally:
        request_id_var.reset(t_rid)
        path_var.reset(t_path)
        method_var.reset(t_method)
        status_code_var.reset(t_status)
        latency_ms_var.reset(t_lat)
        user_id_var.reset(t_user)
        workspace_id_var.reset(t_ws)


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
