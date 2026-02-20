import pytest
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.db.session import engine


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture()
def db_session() -> Session:
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
