from __future__ import annotations

from contextvars import ContextVar

user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
workspace_id_var: ContextVar[str | None] = ContextVar("workspace_id", default=None)

path_var: ContextVar[str | None] = ContextVar("path", default=None)
method_var: ContextVar[str | None] = ContextVar("method", default=None)
status_code_var: ContextVar[int | None] = ContextVar("status_code", default=None)
latency_ms_var: ContextVar[int | None] = ContextVar("latency_ms", default=None)
