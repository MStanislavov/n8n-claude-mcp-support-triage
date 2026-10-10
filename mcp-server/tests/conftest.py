from pathlib import Path

import pytest

from support_mcp import db

KB_DIR = Path(__file__).resolve().parent.parent / "kb"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "support.db"
    db.init_db(path, KB_DIR)
    return path


@pytest.fixture
def conn(db_path: Path):
    connection = db.connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
