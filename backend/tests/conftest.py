import os
import sys
import tempfile
from pathlib import Path
import pytest

# 1. Establish isolated temporary SQLite database path
_test_dir = tempfile.mkdtemp(prefix="claims_test_suite_")
_test_db_path = str(Path(_test_dir) / "claims_test.db")

# 2. Configure environment overrides BEFORE backend modules load
os.environ["DATABASE_PATH"] = _test_db_path
os.environ["LLM_PROVIDER"] = "mock"
os.environ["OTEL_TRACES_CONSOLE"] = "false"

# 3. Patch config module constants in memory
import backend.app.core.config as app_config
app_config.DATABASE_PATH = _test_db_path
app_config.LLM_PROVIDER = "mock"

# 4. Patch database module reference
import backend.app.db.database as app_db
app_db.DATABASE_PATH = _test_db_path

from backend.app.db.database import init_db, get_db_connection

@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """Initializes schema and seed knowledge in the isolated test database once per session."""
    init_db()
    yield
    # Cleanup test database on session completion
    try:
        if os.path.exists(_test_db_path):
            os.remove(_test_db_path)
    except Exception:
        pass

@pytest.fixture(autouse=True)
def clean_test_database_tables():
    """Cleans transactional tables in the isolated test database before each test run."""
    conn = get_db_connection()
    conn.execute("DELETE FROM review_tasks;")
    conn.execute("DELETE FROM audit_events;")
    conn.execute("DELETE FROM simulated_ledger;")
    conn.execute("DELETE FROM claims;")
    conn.commit()
    conn.close()
    yield
