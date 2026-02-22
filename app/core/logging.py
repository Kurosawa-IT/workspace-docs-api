import logging

from app.core.request_id import request_id_var


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = request_id_var.get()
        record.request_id = rid if rid else "-"
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
        )
    )

    root.handlers = [handler]
