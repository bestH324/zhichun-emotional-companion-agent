"""SQLite 持久化：会话元数据 + 全量消息，跨进程重启保留。

仅在显式传入 db_path 时使用；业务层无参构造即为纯内存模式（行为与历史一致）。
"""
import json
import os
import sqlite3
import threading

# 进程级写锁：FastAPI 同步端点跑线程池，多个线程可能并发写同一 sqlite 连接，
# 用单锁串行化写操作，读操作也可复用同一连接（sqlite3 连接默认非线程安全，故统一加锁）。
_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    initial_mbti TEXT,
    current_mbti TEXT,
    turn_count   INTEGER NOT NULL DEFAULT 0,
    facts        TEXT NOT NULL DEFAULT '{}',
    created_at   REAL NOT NULL,
    last_active  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    seq        INTEGER NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, seq);
"""


class Storage:
    """单连接 SQLite 封装，所有公开方法加锁，线程安全。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        if db_path:
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        else:
            self._conn = None

    def close(self) -> None:
        if self._conn is not None:
            with _LOCK:
                self._conn.close()

    # ===== 会话元数据 =====
    def load_session(self, session_id: str) -> dict | None:
        """返回会话元数据 dict（含 facts 已解析为 dict），不存在返回 None。"""
        if self._conn is None:
            return None
        with _LOCK:
            cur = self._conn.execute(
                "SELECT session_id, initial_mbti, current_mbti, turn_count, facts, "
                "created_at, last_active FROM sessions WHERE session_id=?",
                (session_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "session_id": row[0],
            "initial_mbti": row[1],
            "current_mbti": row[2],
            "turn_count": row[3],
            "facts": json.loads(row[4] or "{}"),
            "created_at": row[5],
            "last_active": row[6],
        }

    def save_session(self, session) -> None:
        if self._conn is None:
            return
        with _LOCK:
            self._conn.execute(
                "INSERT INTO sessions (session_id, initial_mbti, current_mbti, "
                "turn_count, facts, created_at, last_active) VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "initial_mbti=excluded.initial_mbti, current_mbti=excluded.current_mbti, "
                "turn_count=excluded.turn_count, facts=excluded.facts, "
                "last_active=excluded.last_active",
                (
                    session.session_id,
                    session.initial_mbti,
                    session.current_mbti,
                    session.turn_count,
                    json.dumps(session.facts, ensure_ascii=False),
                    getattr(session, "created_at", session.last_active),
                    session.last_active,
                ),
            )
            self._conn.commit()

    def save_facts(self, session_id: str, facts: dict) -> None:
        if self._conn is None:
            return
        with _LOCK:
            self._conn.execute(
                "UPDATE sessions SET facts=? WHERE session_id=?",
                (json.dumps(facts, ensure_ascii=False), session_id),
            )
            self._conn.commit()

    def delete_session(self, session_id: str) -> None:
        if self._conn is None:
            return
        with _LOCK:
            self._conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            self._conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
            self._conn.commit()

    # ===== 消息 =====
    def append_message(self, session_id: str, role: str, content: str) -> None:
        if self._conn is None:
            return
        with _LOCK:
            self._conn.execute(
                "INSERT INTO messages (session_id, role, content, seq, created_at) "
                "VALUES (?,?,?, COALESCE((SELECT MAX(seq) FROM messages WHERE session_id=?), 0) + 1, ?)",
                (session_id, role, content, session_id, _now()),
            )
            self._conn.commit()

    def load_messages(self, session_id: str) -> list[dict]:
        """按 seq 升序返回该会话全量消息 [{role, content}]。"""
        if self._conn is None:
            return []
        with _LOCK:
            cur = self._conn.execute(
                "SELECT role, content FROM messages WHERE session_id=? ORDER BY seq",
                (session_id,),
            )
            rows = cur.fetchall()
        return [{"role": r, "content": c} for r, c in rows]


def _now() -> float:
    import time
    return time.time()
