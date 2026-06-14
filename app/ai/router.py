"""统一 AI 服务层 — 支持 OpenAI 和 Anthropic 协议，处理 thinking 内容，支持工具调用"""

import json
from typing import Generator
from app.db import get_session
from app.models.model_config import ModelConfig
from app.ai.web_search import (
    TOOL_DEFINITION_OPENAI, TOOL_DEFINITION_ANTHROPIC,
    execute_tool_call,
)


class AIRouter:
    """统一 AI 服务层"""

    # 最大工具调用轮次，防止无限循环
    MAX_TOOL_ROUNDS = 3

    def __init__(self):
        self._models: dict[str, ModelConfig] = {}
        self._load_models()

    def _load_models(self):
        """从数据库加载模型配置"""
        db = get_session()
        try:
            models = db.query(ModelConfig).filter(ModelConfig.is_active == True).all()
            self._models = {m.id: m for m in models}
        finally:
            db.close()

    def reload(self):
        self._load_models()

    def get_model(self, purpose: str = "all") -> ModelConfig | None:
        """根据用途选择活跃模型"""
        for m in self._models.values():
            if m.purpose == purpose and m.is_active:
                return m
        for m in self._models.values():
            if m.purpose == "all" and m.is_active:
                return m
        for m in self._models.values():
            if m.is_active:
                return m
        return None

    def get_all_models(self) -> list[ModelConfig]:
        return list(self._models.values())

    # ── 同步调用 ─────────────────────────────────────────────

    def chat(self, messages: list[dict], purpose: str = "chat",
             model_id: str | None = None, **kwargs) -> dict:
        """同步对话，返回 {"thinking": str, "content": str}"""
        model = self._resolve_model(model_id, purpose)
        if not model:
            return {"thinking": "", "content": "❌ 未配置 AI 模型，请在设置中添加。"}

        if model.protocol == "anthropic":
            try:
                import anthropic
                return self._call_anthropic(model, messages, **kwargs)
            except ImportError:
                return self._call_openai(model, messages, **kwargs)
        return self._call_openai(model, messages, **kwargs)

    def _call_openai(self, model: ModelConfig, messages: list[dict], **kwargs) -> dict:
        """OpenAI 协议调用"""
        try:
            import openai
        except ImportError as e:
            return {"thinking": "", "content": f"❌ 未安装 openai 库: {e}"}
        except Exception as e:
            return {"thinking": "", "content": f"❌ openai 导入异常: {type(e).__name__}: {e}"}

        client = openai.OpenAI(base_url=model.base_url, api_key=model.api_key)
        try:
            resp = client.chat.completions.create(
                model=model.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
            )
            choice = resp.choices[0]
            thinking = ""
            content = choice.message.content or ""

            if hasattr(choice.message, 'reasoning_content') and choice.message.reasoning_content:
                thinking = choice.message.reasoning_content

            return {"thinking": thinking, "content": content}
        except Exception as e:
            return {"thinking": "", "content": f"❌ AI 调用失败: {e}"}

    def _call_anthropic(self, model: ModelConfig, messages: list[dict], **kwargs) -> dict:
        """Anthropic 协议调用"""
        try:
            import anthropic
        except ImportError:
            return {"thinking": "", "content": "❌ 未安装 anthropic 库"}

        client = anthropic.Anthropic(api_key=model.api_key)
        try:
            system_msg = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append(msg)

            resp = client.messages.create(
                model=model.model_name,
                max_tokens=kwargs.get("max_tokens", 4096),
                system=system_msg if system_msg else anthropic.NOT_GIVEN,
                messages=user_messages,
            )

            thinking = ""
            content = ""
            for block in resp.content:
                if block.type == "thinking":
                    thinking = block.thinking
                elif block.type == "text":
                    content = block.text

            return {"thinking": thinking, "content": content}
        except Exception as e:
            return {"thinking": "", "content": f"❌ AI 调用失败: {e}"}

    # ── 流式调用（支持工具调用）─────────────────────────────────

    def stream_chat(self, messages: list[dict], purpose: str = "chat",
                    model_id: str | None = None, **kwargs) -> Generator[dict, None, None]:
        """流式对话，yield {"type": "thinking"|"content"|"tool_call"|"tool_result", "data": str}"""
        model = self._resolve_model(model_id, purpose)
        if not model:
            yield {"type": "content", "data": "❌ 未配置 AI 模型"}
            return

        if model.protocol == "anthropic":
            try:
                import anthropic
                yield from self._stream_anthropic_with_tools(model, messages, **kwargs)
            except ImportError:
                yield from self._stream_openai_with_tools(model, messages, **kwargs)
        else:
            yield from self._stream_openai_with_tools(model, messages, **kwargs)

    def _stream_openai_with_tools(self, model: ModelConfig, messages: list[dict], **kwargs):
        """OpenAI 协议流式调用，支持工具调用循环"""
        try:
            import openai
        except ImportError as e:
            yield {"type": "content", "data": f"❌ 未安装 openai 库: {e}"}
            return
        except Exception as e:
            yield {"type": "content", "data": f"❌ openai 导入异常: {type(e).__name__}: {e}"}
            return

        client = openai.OpenAI(base_url=model.base_url, api_key=model.api_key)
        current_messages = list(messages)

        for round_num in range(self.MAX_TOOL_ROUNDS + 1):
            try:
                stream = client.chat.completions.create(
                    model=model.model_name,
                    messages=current_messages,
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 4096),
                    tools=[TOOL_DEFINITION_OPENAI],
                    tool_choice="auto",
                    stream=True,
                )

                # 收集本轮的工具调用和文本内容
                tool_calls = {}  # index -> {id, name, arguments}
                has_tool_call = False

                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    # 处理 thinking（DeepSeek）
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        yield {"type": "thinking", "data": delta.reasoning_content}

                    # 处理文本内容
                    if delta.content:
                        yield {"type": "content", "data": delta.content}

                    # 处理工具调用
                    if delta.tool_calls:
                        has_tool_call = True
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls:
                                tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tool_calls[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls[idx]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls[idx]["arguments"] += tc.function.arguments

                # 如果没有工具调用，流式结束
                if not has_tool_call:
                    return

                # 执行工具调用
                for idx in sorted(tool_calls.keys()):
                    tc = tool_calls[idx]
                    if tc["name"] == "web_search":
                        # 解析参数获取查询词
                        try:
                            args = json.loads(tc["arguments"])
                            query = args.get("query", "")
                        except (json.JSONDecodeError, KeyError):
                            query = ""

                        yield {"type": "tool_call", "data": json.dumps({
                            "name": "web_search", "query": query
                        }, ensure_ascii=False)}

                        result = execute_tool_call(tc["arguments"])

                        yield {"type": "tool_result", "data": json.dumps({
                            "name": "web_search", "query": query, "result": result
                        }, ensure_ascii=False)}

                        # 将工具调用和结果添加到消息历史
                        current_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": tc["arguments"],
                                }
                            }]
                        })
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        })

            except Exception as e:
                yield {"type": "content", "data": f"\n\n❌ 流式调用失败: {e}"}
                return

    def _stream_anthropic_with_tools(self, model: ModelConfig, messages: list[dict], **kwargs):
        """Anthropic 协议流式调用，支持工具调用循环"""
        try:
            import anthropic
        except ImportError:
            yield {"type": "content", "data": "❌ 未安装 anthropic 库"}
            return

        client = anthropic.Anthropic(api_key=model.api_key)

        # 分离 system 消息
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        current_messages = list(user_messages)

        for round_num in range(self.MAX_TOOL_ROUNDS + 1):
            try:
                with client.messages.stream(
                    model=model.model_name,
                    max_tokens=kwargs.get("max_tokens", 4096),
                    system=system_msg if system_msg else anthropic.NOT_GIVEN,
                    messages=current_messages,
                    tools=[TOOL_DEFINITION_ANTHROPIC],
                ) as stream:
                    # 收集本轮的工具调用
                    tool_use_blocks = []  # {id, name, input_json}
                    current_tool_id = None
                    current_tool_name = None
                    current_tool_input = ""
                    in_tool_use = False

                    for event in stream:
                        if event.type == "content_block_start":
                            if hasattr(event.content_block, 'type'):
                                if event.content_block.type == "tool_use":
                                    in_tool_use = True
                                    current_tool_id = event.content_block.id
                                    current_tool_name = event.content_block.name
                                    current_tool_input = ""
                        elif event.type == "content_block_delta":
                            if hasattr(event.delta, 'thinking'):
                                yield {"type": "thinking", "data": event.delta.thinking}
                            elif hasattr(event.delta, 'text'):
                                yield {"type": "content", "data": event.delta.text}
                            elif hasattr(event.delta, 'partial_json') and in_tool_use:
                                current_tool_input += event.delta.partial_json
                        elif event.type == "content_block_stop":
                            if in_tool_use:
                                tool_use_blocks.append({
                                    "id": current_tool_id,
                                    "name": current_tool_name,
                                    "input_json": current_tool_input,
                                })
                                in_tool_use = False

                # 如果没有工具调用，流式结束
                if not tool_use_blocks:
                    return

                # 执行工具调用
                tool_results = []
                for tu in tool_use_blocks:
                    if tu["name"] == "web_search":
                        try:
                            args = json.loads(tu["input_json"])
                            query = args.get("query", "")
                        except (json.JSONDecodeError, KeyError):
                            query = ""

                        yield {"type": "tool_call", "data": json.dumps({
                            "name": "web_search", "query": query
                        }, ensure_ascii=False)}

                        result = execute_tool_call(tu["input_json"])

                        yield {"type": "tool_result", "data": json.dumps({
                            "name": "web_search", "query": query, "result": result
                        }, ensure_ascii=False)}

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu["id"],
                            "content": result,
                        })

                # 将助手的工具调用和工具结果添加到消息历史
                assistant_content = []
                for tu in tool_use_blocks:
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tu["id"],
                        "name": tu["name"],
                        "input": json.loads(tu["input_json"]),
                    })
                current_messages.append({"role": "assistant", "content": assistant_content})
                current_messages.append({"role": "user", "content": tool_results})

            except Exception as e:
                yield {"type": "content", "data": f"\n\n❌ 流式调用失败: {e}"}
                return

    def _resolve_model(self, model_id: str | None, purpose: str) -> ModelConfig | None:
        if model_id and model_id in self._models:
            return self._models[model_id]
        return self.get_model(purpose)
