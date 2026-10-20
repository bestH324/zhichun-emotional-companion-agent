"""Session + SessionManager：会话级状态隔离、并发安全、TTL 清理。"""
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from app.config import (
    CLEANUP_INTERVAL_SECONDS,
    DB_PATH,
    DEFAULT_MBTI,
    SHORT_TERM_N,
    TTL_SECONDS,
)
from app.modules.storage import Storage
from app.schemas import Message


@dataclass
class Session:
    session_id: str
    turn_count: int = 0
    initial_mbti: str | None = None          # 用户初始选择，None 表示未选
    current_mbti: str = DEFAULT_MBTI          # 当前周期生效人格
    cycle_portraits: list[str] = field(default_factory=list)  # 本周期切片画像累积（最多 CYCLE_SLICES 个）
    slice_buffer: list = field(default_factory=list)       # 本切片累积消息（最多 SLICE_SIZE 轮，供推断用）
    short_term: deque = field(default_factory=deque)       # 最近 N 轮 list[Message]
    episodic: list[str] = field(default_factory=list)      # 全历史文本（关键词召回）
    facts: dict[str, str] = field(default_factory=dict)    # 事实画像
    last_active: float = field(default_factory=time.time)  # 最后活跃时间戳
    # 单会话串行锁：同一 session 的操作顺序执行，不同 session 之间互不影响（§4.8.2）
    lock: threading.RLock = field(
        default_factory=threading.RLock, repr=False, compare=False
    )


class SessionManager:
    def __init__(self, ttl_seconds: int = TTL_SECONDS, db_path: str | None = None):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds
        self._cleanup_thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        # db_path 为空 = 纯内存模式（历史行为，测试无参构造走这里）
        self._storage = Storage(db_path) if db_path else None

    def get_or_create(self, session_id: str) -> Session:
        """空 id → 服务端生成 uuid4；非空 id 仅在命中「已存在且未过期」会话时续接，
        否则忽略传入值、服务端生成新 uuid4（防枚举 / 会话劫持，见规划书 §4.8.2）。

        持久化模式下，内存 miss 时先从 SQLite 恢复；恢复出且未过期则续接，
        过期或不存在则新建（新建写入 SQLite）。
        """
        now = time.time()
        with self._lock:
            if session_id:
                sess = self._sessions.get(session_id)
                if sess is not None:
                    if now - sess.last_active > self.ttl_seconds:
                        # TTL 到期：清理旧会话，走下方新建
                        del self._sessions[session_id]
                    else:
                        sess.last_active = now
                        self.save(sess)
                        return sess
                # 内存 miss：尝试从 SQLite 恢复
                restored = self._restore(session_id, now)
                if restored is not None:
                    self._sessions[restored.session_id] = restored
                    return restored
            # 新建：服务端生成不可枚举的 uuid4
            new_id = uuid.uuid4().hex
            sess = Session(session_id=new_id)
            self._sessions[new_id] = sess
            self.save(sess)
            return sess

    def _restore(self, session_id: str, now: float) -> Session | None:
        """从 SQLite 恢复会话；仅当存在且未过期时返回 Session，否则返回 None。"""
        if self._storage is None:
            return None
        meta = self._storage.load_session(session_id)
        if meta is None:
            return None
        if now - meta["last_active"] > self.ttl_seconds:
            # 过期：删除持久化记录，不恢复
            self._storage.delete_session(session_id)
            return None
        sess = Session(
            session_id=meta["session_id"],
            turn_count=meta["turn_count"],
            initial_mbti=meta["initial_mbti"],
            current_mbti=meta["current_mbti"],
        )
        sess.facts = meta["facts"]
        sess.last_active = now
        # 重建记忆：episodic = 全量历史文本；short_term = 最近 N 轮（2N 条）
        msgs = self._storage.load_messages(session_id)
        sess.episodic = [m["content"] for m in msgs]
        recent = msgs[-SHORT_TERM_N * 2:]
        sess.short_term = deque(
            Message(role=m["role"], content=m["content"]) for m in recent
        )
        return sess

    def save(self, sess: Session) -> None:
        """持久化会话元数据（turn_count / current_mbti / facts / last_active）。
        纯内存模式下为空操作。"""
        if self._storage is not None:
            self._storage.save_session(sess)

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return None
            if time.time() - sess.last_active > self.ttl_seconds:
                del self._sessions[session_id]
                return None
            sess.last_active = time.time()
            return sess

    def touch(self, session_id: str) -> None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is not None:
                sess.last_active = time.time()

    def end(self, session_id: str) -> bool:
        """显式结束会话，返回是否真实存在（幂等：不存在返回 False）。

        遵守单会话串行：先取会话引用并等待其进行中的操作（process_chat 等）完成，
        再原子移除。锁顺序为 session.lock → self._lock，与业务代码不交叉，无死锁。
        """
        with self._lock:
            sess = self._sessions.get(session_id)
        if sess is None:
            return False
        with sess.lock:  # 等待该会话正在进行的对话结束
            with self._lock:
                removed = self._sessions.pop(session_id, None) is not None
            if removed and self._storage is not None:
                self._storage.delete_session(session_id)
            return removed

    def count(self) -> int:
        """当前活跃会话数（含尚未被清理的过期会话）。"""
        with self._lock:
            return len(self._sessions)

    def cleanup(self) -> int:
        """清理 TTL 过期会话，返回清理数量。"""
        now = time.time()
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if now - s.last_active > self.ttl_seconds
            ]
            for sid in expired:
                self._sessions.pop(sid, None)
        return len(expired)

    # ===== 后台自动清理（规划书 §4.8.2「不活跃自动清理」）=====
    def start_cleanup(self, interval_seconds: float = CLEANUP_INTERVAL_SECONDS) -> None:
        """启动后台 daemon 线程周期性执行 cleanup；幂等，已启动则不重复启动。"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return
        self._stop_event = threading.Event()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, args=(interval_seconds,), daemon=True
        )
        self._cleanup_thread.start()

    def stop_cleanup(self) -> None:
        """停止后台清理线程（触发停止信号并 join）。"""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._cleanup_thread is not None:
            self._cleanup_thread.join(timeout=5)
            self._cleanup_thread = None
        self._stop_event = None

    def _cleanup_loop(self, interval_seconds: float) -> None:
        while not self._stop_event.wait(interval_seconds):
            self.cleanup()


# 进程级单例（只读依赖，无业务可变状态）
# 上线时按 DB_PATH 启用持久化；默认（空）保持内存模式，兼容既有测试。
session_manager = SessionManager(db_path=DB_PATH or None)
