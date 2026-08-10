"""统一数据库管理 — SQLAlchemy + SQLite"""

import os
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.utils.paths import get_data_dir


_db_override = os.environ.get("NEXUS_DB_PATH", "").strip()
if _db_override == ":memory:":
    DATABASE_PATH: Path | None = None
    DATABASE_URL = "sqlite://"
elif _db_override:
    DATABASE_PATH = Path(_db_override).expanduser().resolve()
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
else:
    DATABASE_PATH = get_data_dir() / "nexus.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

_engine_kwargs = {
    "echo": False,
    "connect_args": {"check_same_thread": False, "timeout": 30},
}
if DATABASE_PATH is None:
    # 测试进程中的所有 Session 共享同一个内存数据库连接。
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)

# 启用 WAL 模式 + busy_timeout
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout = 10000")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def init_db():
    """创建所有表 + FTS5 索引 + 增量迁移"""
    import app.models  # noqa: F401 — 触发模型注册
    Base.metadata.create_all(bind=engine)

    # 增量迁移: 添加缺失列
    _migrate_columns()

    # Create indexes after migrations so upgraded databases receive them on
    # the same startup that adds any required columns.
    _ensure_performance_indexes()

    # 初始化 FTS5 全文索引
    try:
        from app.search.fts import init_fts
        session = SessionLocal()
        init_fts(session)
        session.close()
    except Exception as e:
        print(f"[db] FTS5 初始化失败（非致命）: {e}")


def _ensure_performance_indexes():
    """Create indexes needed by the application's high-frequency query paths."""
    statements = (
        "CREATE INDEX IF NOT EXISTS ix_tasks_date_completed_sort ON tasks (date, completed, sort_order)",
        "CREATE INDEX IF NOT EXISTS ix_tasks_completed_at ON tasks (completed_at)",
        "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created ON chat_messages (session_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_chat_sessions_category_created ON chat_sessions (category, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_experiments_user_status_updated ON experiments (user_id, status, updated_at)",
        "CREATE INDEX IF NOT EXISTS ix_experiment_results_experiment_version ON experiment_results (experiment_id, version)",
        "CREATE INDEX IF NOT EXISTS ix_card_tags_tag_card ON card_tags (tag_name, card_id)",
        "CREATE INDEX IF NOT EXISTS ix_knowledge_source_updated ON knowledge_cards (source_type, updated_at)",
        "CREATE INDEX IF NOT EXISTS ix_paper_category_links_category_paper ON paper_category_links (category_id, paper_id)",
        "CREATE INDEX IF NOT EXISTS ix_papers_created_at ON papers (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_papers_year_star ON papers (year, star_rating)",
        "CREATE INDEX IF NOT EXISTS ix_search_history_created_at ON search_history (created_at)",
    )
    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception as exc:
                # Legacy installations may receive missing columns later in the
                # startup migration.  Do not make the application unbootable;
                # the index will be created on the next startup.
                print(f"[db] index creation deferred: {exc}")


def get_session():
    """获取数据库会话（调用方负责关闭）"""
    return SessionLocal()


def get_database_path() -> Path | None:
    """返回当前 SQLite 文件；内存测试数据库返回 None。"""
    return DATABASE_PATH


def _migrate_columns():
    """检查并添加缺失的列（增量迁移）"""
    import sqlite3
    db_path = get_database_path()
    if db_path is None or not db_path.exists():
        return
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查 chat_sessions 是否有 import_group_id
        cursor.execute("PRAGMA table_info(chat_sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'import_group_id' not in columns:
            cursor.execute(
                "ALTER TABLE chat_sessions ADD COLUMN import_group_id TEXT "
                "REFERENCES import_groups(id) ON DELETE SET NULL"
            )
            conn.commit()
            print("[db] 迁移: 添加 chat_sessions.import_group_id 列")

        conn.close()
    except Exception as e:
        print(f"[db] 迁移失败（非致命）: {e}")
