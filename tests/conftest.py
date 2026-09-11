import pytest
import tempfile
from pathlib import Path
from src.database.connection import init_db, seed_demo_data

@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_finance.db"
        init_db(db_path)
        seed_demo_data(db_path, force=True)
        yield db_path
