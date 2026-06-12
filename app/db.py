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
    """创建所有表"""
    import app.models  # noqa: F401 — 触发模型注册
    Base.metadata.create_all(bind=engine)


def get_session():
    """获取数据库会话（调用方负责关闭）"""
    return SessionLocal()
