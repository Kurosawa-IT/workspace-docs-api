from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from typing import Any

from app.core.log_context import (
    latency_ms_var,
    method_var,
    path_var,
    status_code_var,
    user_id_var,
    workspace_id_var,
)
from app.core.request_id import request_id_var


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.workspace_id = workspace_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        record.path = path_var.get() or "-"
        record.method = method_var.get() or "-"
        record.status_code = status_code_var.get() if status_code_var.get() is not None else "-"
        record.latency_ms = latency_ms_var.get() if latency_ms_var.get() is not None else "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "workspace_id": getattr(record, "workspace_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "path": getattr(record, "path", "-"),
            "method": getattr(record, "method", "-"),
            "status_code": getattr(record, "status_code", "-"),
            "latency_ms": getattr(record, "latency_ms", "-"),
        }

        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event

        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "stacktrace": "".join(traceback.format_exception(*record.exc_info)),
            }

        return json.dumps(payload, ensure_ascii=False)


def init_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.access").disabled = True

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False
        lg.setLevel(level)
