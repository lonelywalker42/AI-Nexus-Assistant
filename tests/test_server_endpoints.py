"""FastAPI 端点测试用例。

测试 v4.4.0 修复:
- /api/knowledge/cards 卡片列表
- /api/papers/fetch-pdf 错误状态码映射
- /api/dashboard 健康检查
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="module")
def client():
    """提供 FastAPI TestClient。"""
    from fastapi.testclient import TestClient
    # 使用临时数据库
    os.environ.setdefault("NEXUS_DB_PATH", ":memory:")
    from server import app
    return TestClient(app)


class TestDashboardEndpoint:
    """测试 Dashboard 端点。"""

    def test_dashboard_ok(self, client):
        """GET /api/dashboard 应返回 200。"""
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        # dashboard 返回包含统计信息的对象
        assert isinstance(data, dict)
        assert len(data) > 0


class TestPerformanceEndpoints:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_week_tasks_are_batched(self, client):
        resp = client.get("/api/tasks/week?start=2026-08-10")
        assert resp.status_code == 200
        assert len(resp.json()) == 7

    def test_paper_categories_static_route(self, client):
        resp = client.get("/api/papers/categories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestKnowledgeCardsEndpoint:
    """测试知识卡片端点。"""

    def test_list_cards_empty(self, client):
        """GET /api/knowledge/cards 应返回列表。"""
        resp = client.get("/api/knowledge/cards")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_cards_with_search(self, client):
        """带搜索参数应正常返回。"""
        resp = client.get("/api/knowledge/cards?search=test")
        assert resp.status_code == 200

    def test_list_cards_with_source_type(self, client):
        """带来源类型过滤应正常返回。"""
        resp = client.get("/api/knowledge/cards?source_type=manual")
        assert resp.status_code == 200


class TestModelsEndpoint:
    """测试模型配置端点。"""

    def test_list_models(self, client):
        """GET /api/models 应返回列表。"""
        resp = client.get("/api/models")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestTasksEndpoint:
    """测试任务端点。"""

    def test_list_tasks(self, client):
        """GET /api/tasks 应返回列表。"""
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestFetchPdfErrorMapping:
    """测试 PDF 拉取错误状态码映射 (v4.4.0 修复)。"""

    def test_missing_params_returns_400(self, client):
        """无参数应返回 400。"""
        resp = client.post("/api/papers/fetch-pdf", json={"doi": "", "title": ""})
        assert resp.status_code == 400

    def test_invalid_doi_returns_422_or_502(self, client):
        """无效 DOI 应返回 422（输入无效）或 502（网络失败）。"""
        resp = client.post("/api/papers/fetch-pdf", json={"doi": "invalid-doi", "title": ""})
        # 根据错误类型，应返回 422（无效输入）或 502（网络拉取失败）
        assert resp.status_code in (422, 502, 504)
        data = resp.json()
        assert "detail" in data
        # 错误信息应是中文提示，而非原始 "API Error 422"
        assert len(data["detail"]) > 0


class TestChatEndpoint:
    """测试聊天端点基础可用性。"""

    def test_list_sessions(self, client):
        """GET /api/chat/sessions 应返回列表。"""
        resp = client.get("/api/chat/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
