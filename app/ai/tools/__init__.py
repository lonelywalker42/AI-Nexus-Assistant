"""AI 工具注册框架 — 统一管理 OpenAI/Anthropic 格式的工具定义和执行"""

import json
from typing import Callable

# 工具注册表
_registry: dict[str, dict] = {}


def register_tool(name: str, description: str, parameters: dict,
                  handler: Callable[[str], str],
                  openai_schema: dict | None = None,
                  anthropic_schema: dict | None = None):
    """注册一个 AI 工具

    Args:
        name: 工具名称
        description: 工具描述
        parameters: JSON Schema 格式的参数定义
        handler: 执行函数，接收 JSON 字符串参数，返回字符串结果
        openai_schema: 可选的自定义 OpenAI 格式（不传则自动生成）
        anthropic_schema: 可选的自定义 Anthropic 格式（不传则自动生成）
    """
    if openai_schema is None:
        openai_schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        }
    if anthropic_schema is None:
        anthropic_schema = {
            "name": name,
            "description": description,
            "input_schema": parameters,
        }

    _registry[name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "handler": handler,
        "openai_schema": openai_schema,
        "anthropic_schema": anthropic_schema,
    }


def get_all_openai_tools() -> list[dict]:
    """获取所有工具的 OpenAI 格式定义"""
    return [t["openai_schema"] for t in _registry.values()]


def get_all_anthropic_tools() -> list[dict]:
    """获取所有工具的 Anthropic 格式定义"""
    return [t["anthropic_schema"] for t in _registry.values()]


def get_openai_tool(name: str) -> dict | None:
    """获取单个工具的 OpenAI 格式"""
    t = _registry.get(name)
    return t["openai_schema"] if t else None


def get_anthropic_tool(name: str) -> dict | None:
    """获取单个工具的 Anthropic 格式"""
    t = _registry.get(name)
    return t["anthropic_schema"] if t else None


def execute_tool(name: str, arguments_json: str) -> str:
    """执行工具调用"""
    t = _registry.get(name)
    if not t:
        return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
    try:
        return t["handler"](arguments_json)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def get_tool_names() -> list[str]:
    """获取所有已注册工具名"""
    return list(_registry.keys())


# 导入各工具模块以触发注册
def init_tools():
    """初始化所有工具（延迟导入避免循环依赖）"""
    from app.ai.tools import paper_tool  # noqa: F401
    from app.ai.tools import knowledge_tool  # noqa: F401
    from app.ai.tools import experiment_tool  # noqa: F401
    from app.ai.tools import academic_tool  # noqa: F401
