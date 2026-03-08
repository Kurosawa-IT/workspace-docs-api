from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal

router = APIRouter(tags=["debug"])


@router.post("/debug/force-db-error")
def force_db_error():
    if settings.app_env not in {"local", "test", "ci"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    with SessionLocal() as db:
        db.execute(text("SELECT * FROM __non_existent_table_for_drill__"))
    return {"ok": True}
