import json
import os
import threading
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


def _serialize_session(data: dict) -> dict:
    out = {}
    for k, v in data.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _serialize_session(v)
        elif isinstance(v, list):
            out[k] = [_serialize_session(i) if isinstance(i, dict) else i.isoformat() if isinstance(i, datetime) else i for i in v]
        else:
            out[k] = v
    return out


def _deserialize_session(data: dict) -> dict:
    out = {}
    for k, v in data.items():
        if isinstance(v, str) and k in ("createdAt", "updatedAt"):
            try:
                out[k] = datetime.fromisoformat(v)
            except (ValueError, TypeError):
                out[k] = v
        elif isinstance(v, dict):
            out[k] = _deserialize_session(v)
        elif isinstance(v, list):
            out[k] = [_deserialize_session(i) if isinstance(i, dict) else i for i in v]
        else:
            out[k] = v
    return out


class MemoryStore:
    def __init__(self, ttl_minutes: int = 45, tmp_dir: str = "./tmp/sessions"):
        self._store: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self.ttl = timedelta(minutes=ttl_minutes)
        self._tmp_dir = tmp_dir
        self._start_cleaner()
        self._load_from_disk()

    def _state_path(self, session_id: str) -> str:
        return os.path.join(self._tmp_dir, session_id, "state.json")

    def _save_to_disk(self, session_id: str):
        try:
            path = self._state_path(session_id)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = _serialize_session(self._store[session_id])
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist session {session_id}: {e}")

    def _load_from_disk(self):
        loaded = 0
        if not os.path.isdir(self._tmp_dir):
            return
        for sid_dir in os.listdir(self._tmp_dir):
            state_file = os.path.join(self._tmp_dir, sid_dir, "state.json")
            if os.path.isfile(state_file):
                try:
                    with open(state_file, "r") as f:
                        data = json.load(f)
                    self._store[sid_dir] = _deserialize_session(data)
                    loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load session {sid_dir}: {e}")
        if loaded:
            logger.info(f"Loaded {loaded} sessions from disk")

    def create(self, session_id: str, data: dict):
        with self._lock:
            self._store[session_id] = data
            self._save_to_disk(session_id)
            logger.info(f"Store create {session_id} size={len(self._store)}")

    def get(self, session_id: str) -> Optional[dict]:
        with self._lock:
            return self._store.get(session_id)

    def update(self, session_id: str, patch: dict):
        with self._lock:
            if session_id in self._store:
                self._store[session_id].update(patch)
                self._store[session_id]["updatedAt"] = datetime.utcnow()
                self._save_to_disk(session_id)

    def set(self, session_id: str, data: dict):
        with self._lock:
            self._store[session_id] = data
            self._save_to_disk(session_id)

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


store: Optional[MemoryStore] = None

def init_store(ttl_minutes: int, tmp_dir: str = "./tmp/sessions"):
    global store
    store = MemoryStore(ttl_minutes=ttl_minutes, tmp_dir=tmp_dir)
    return store

def get_store() -> MemoryStore:
    if store is None:
        raise RuntimeError("Store not initialized")
    return store
