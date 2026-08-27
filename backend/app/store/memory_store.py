import threading
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

class MemoryStore:
    def __init__(self, ttl_minutes: int = 45):
        self._store: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self.ttl = timedelta(minutes=ttl_minutes)
        self._start_cleaner()

    def create(self, session_id: str, data: dict):
        with self._lock:
            self._store[session_id] = data
            logger.info(f"Store create {session_id} size={len(self._store)}")

    def get(self, session_id: str) -> Optional[dict]:
        with self._lock:
            return self._store.get(session_id)

    def update(self, session_id: str, patch: dict):
        with self._lock:
            if session_id in self._store:
                self._store[session_id].update(patch)
                # ensure nested updates merge? caller should provide full object for nested
                self._store[session_id]["updatedAt"] = datetime.utcnow()

    def set(self, session_id: str, data: dict):
        with self._lock:
            self._store[session_id] = data

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False

    def list_ids(self):
        with self._lock:
            return list(self._store.keys())

    def _start_cleaner(self):
        def cleaner():
            while True:
                time.sleep(60)
                now = datetime.utcnow()
                expired = []
                with self._lock:
                    for sid, sess in list(self._store.items()):
                        created = sess.get("createdAt")
                        if isinstance(created, str):
                            try:
                                created = datetime.fromisoformat(created)
                            except:
                                continue
                        if created and now - created > self.ttl:
                            expired.append(sid)
                    for sid in expired:
                        del self._store[sid]
                if expired:
                    logger.info(f"Cleaner expired {len(expired)} sessions: {expired}")

        t = threading.Thread(target=cleaner, daemon=True)
        t.start()

# global singleton - initialized in main.py with config
store: Optional[MemoryStore] = None

def init_store(ttl_minutes: int):
    global store
    store = MemoryStore(ttl_minutes=ttl_minutes)
    return store

def get_store() -> MemoryStore:
    if store is None:
        raise RuntimeError("Store not initialized")
    return store
