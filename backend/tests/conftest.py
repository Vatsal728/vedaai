import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ensure store initialized for tests
import pytest
from app.store.memory_store import init_store

@pytest.fixture(autouse=True)
def setup_store():
    init_store(ttl_minutes=45)
    yield
