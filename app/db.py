"""统一数据库管理 — SQLAlchemy + SQLite"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.utils.paths import get_data_dir


DATABASE_URL = f"sqlite:///{get_data_dir() / 'nexus.db'}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# 启用 WAL 模式
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
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

    # 初始化 FTS5 全文索引
    try:
        from app.search.fts import init_fts
        session = SessionLocal()
        init_fts(session)
        session.close()
    except Exception as e:
        print(f"[db] FTS5 初始化失败（非致命）: {e}")


def get_session():
    """获取数据库会话（调用方负责关闭）"""
    return SessionLocal()


def _migrate_columns():
    """检查并添加缺失的列（增量迁移）"""
    import sqlite3
    db_path = get_data_dir() / 'nexus.db'
    if not db_path.exists():
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
