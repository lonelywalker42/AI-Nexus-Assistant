"""知识卡片与任务服务测试用例。

测试 v4.4.0 修复的功能:
- 卡片 CRUD 和过滤
- DeepSeek JSON 解析
- 任务服务回归测试
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def db_session(tmp_path):
    """提供隔离的临时数据库会话。"""
    import app.db as db_module
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    # 创建临时数据库引擎
    db_path = str(tmp_path / "test.db")
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(test_engine, "connect")
    def _set_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout = 10000")
        cursor.close()

    # 替换全局引擎和会话工厂
    original_engine = db_module.engine
    original_session_local = db_module.SessionLocal
    db_module.engine = test_engine
    db_module.SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, expire_on_commit=False,
    )

    # 初始化表
    from app.db import init_db, get_session
    init_db()
    session = get_session()
    yield session
    session.close()

    # 恢复原始引擎
    db_module.engine = original_engine
    db_module.SessionLocal = original_session_local


class TestKnowledgeService:
    """测试知识卡片服务。"""

    def test_create_card(self, db_session):
        """应能创建知识卡片。"""
        from app.services import knowledge_service
        card = knowledge_service.create_card(
            db_session,
            title="测试卡片",
            summary="这是一个测试",
            key_points=["要点1", "要点2"],
            source_type="manual",
        )
        assert card is not None
        assert card.title == "测试卡片"
        assert card.summary == "这是一个测试"

    def test_get_cards_returns_list(self, db_session):
        """get_cards 应返回列表。"""
        from app.services import knowledge_service
        cards = knowledge_service.get_cards(db_session)
        assert isinstance(cards, list)

    def test_get_cards_search_filter(self, db_session):
        """应支持按关键词搜索卡片。"""
        from app.services import knowledge_service
        knowledge_service.create_card(
            db_session, title="机器学习基础", summary="介绍ML概念",
            key_points=[], source_type="manual",
        )
        knowledge_service.create_card(
            db_session, title="深度学习综述", summary="介绍DL概念",
            key_points=[], source_type="manual",
        )
        cards = knowledge_service.get_cards(db_session, search="机器")
        assert len(cards) == 1
        assert cards[0].title == "机器学习基础"

    def test_get_cards_source_type_filter(self, db_session):
        """应支持按来源类型过滤。"""
        from app.services import knowledge_service
        knowledge_service.create_card(
            db_session, title="手动卡片", summary="手动创建",
            key_points=[], source_type="manual",
        )
        knowledge_service.create_card(
            db_session, title="导入卡片", summary="从DeepSeek导入",
            key_points=[], source_type="deepseek",
        )
        cards = knowledge_service.get_cards(db_session, source_type="deepseek")
        assert len(cards) == 1
        assert cards[0].source_type == "deepseek"

    def test_update_card_star_rating(self, db_session):
        """应能更新卡片评分。"""
        from app.services import knowledge_service
        card = knowledge_service.create_card(
            db_session, title="测试卡片", summary="摘要",
            key_points=[], source_type="manual",
        )
        updated = knowledge_service.update_card(db_session, card.id, star_rating=5)
        assert updated.star_rating == 5

    def test_delete_card(self, db_session):
        """应能删除卡片。"""
        from app.services import knowledge_service
        card = knowledge_service.create_card(
            db_session, title="待删除", summary="摘要",
            key_points=[], source_type="manual",
        )
        result = knowledge_service.delete_card(db_session, card.id)
        assert result is True

    def test_get_card_not_found(self, db_session):
        """获取不存在的卡片应返回 None。"""
        from app.services import knowledge_service
        card = knowledge_service.get_card(db_session, "nonexistent-id")
        assert card is None


class TestDeepSeekImportService:
    """测试 DeepSeek 导入服务。"""

    def test_parse_deepseek_json_empty(self):
        """空数据应返回空列表。"""
        from app.services.deepseek_import_service import parse_deepseek_json
        sessions = parse_deepseek_json([])
        assert sessions == []

    def test_parse_deepseek_json_dict(self):
        """字典格式（单个对话）应返回列表。"""
        from app.services.deepseek_import_service import parse_deepseek_json
        data = {"id": "conv_1", "title": "对话", "mapping": {}}
        sessions = parse_deepseek_json(data)
        assert isinstance(sessions, list)

    def test_walk_mapping_empty(self):
        """空 mapping 应返回空列表。"""
        from app.services.deepseek_import_service import walk_mapping
        messages = walk_mapping({}, "root")
        assert messages == []

    def test_walk_mapping_missing_node(self):
        """不存在的 node_id 应返回空列表。"""
        from app.services.deepseek_import_service import walk_mapping
        messages = walk_mapping({"other": {}}, "root")
        assert messages == []


class TestTaskService:
    """测试任务服务（回归测试）。"""

    def test_add_standalone_task(self, db_session):
        """应能创建独立任务。"""
        from app.services import task_service
        from datetime import date
        task = task_service.add_standalone_task(
            db_session,
            date_str=date.today().isoformat(),
            content="测试任务",
            priority="normal",
            category="general",
        )
        assert task is not None

    def test_get_todos_by_date(self, db_session):
        """应能按日期获取任务列表。"""
        from app.services import task_service
        from datetime import date
        task_service.add_standalone_task(
            db_session,
            date_str=date.today().isoformat(),
            content="今日任务",
        )
        tasks = task_service.get_todos_by_date(db_session, date.today().isoformat())
        assert isinstance(tasks, list)
        assert len(tasks) >= 1

    def test_toggle_complete(self, db_session):
        """应能切换任务完成状态。"""
        from app.services import task_service
        from datetime import date
        task = task_service.add_standalone_task(
            db_session,
            date_str=date.today().isoformat(),
            content="待切换",
        )
        toggled = task_service.toggle_complete(db_session, task.id)
        assert toggled is not None
        assert toggled.completed is True

    def test_delete_task(self, db_session):
        """应能删除任务。"""
        from app.services import task_service
        from datetime import date
        task = task_service.add_standalone_task(
            db_session,
            date_str=date.today().isoformat(),
            content="待删除",
        )
        result = task_service.delete_task(db_session, task.id)
        assert result is True
