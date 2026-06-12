"""统一 AI 服务层 — 支持 OpenAI 和 Anthropic 协议，处理 thinking 内容"""

import json
from typing import AsyncGenerator, Generator
from app.db import get_session
from app.models.model_config import ModelConfig


class AIRouter:
    """统一 AI 服务层"""

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
        # 先找精确匹配
        for m in self._models.values():
            if m.purpose == purpose and m.is_active:
                return m
        # 再找 all
        for m in self._models.values():
            if m.purpose == "all" and m.is_active:
                return m
        # 返回第一个活跃的
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
            return self._call_anthropic(model, messages, **kwargs)
        return self._call_openai(model, messages, **kwargs)

    def _call_openai(self, model: ModelConfig, messages: list[dict], **kwargs) -> dict:
        """OpenAI 协议调用"""
        try:
            import openai
        except ImportError:
            return {"thinking": "", "content": "❌ 未安装 openai 库"}

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

            # 处理 DeepSeek thinking 模式
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
            # 分离 system 消息
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

    # ── 流式调用 ─────────────────────────────────────────────

    def stream_chat(self, messages: list[dict], purpose: str = "chat",
                    model_id: str | None = None, **kwargs) -> Generator[dict, None, None]:
        """流式对话，yield {"type": "thinking"|"content", "data": str}"""
        model = self._resolve_model(model_id, purpose)
        if not model:
            yield {"type": "content", "data": "❌ 未配置 AI 模型"}
            return

        if model.protocol == "anthropic":
            yield from self._stream_anthropic(model, messages, **kwargs)
        else:
            yield from self._stream_openai(model, messages, **kwargs)

    def _stream_openai(self, model: ModelConfig, messages: list[dict], **kwargs):
        try:
            import openai
        except ImportError:
            yield {"type": "content", "data": "❌ 未安装 openai 库"}
            return

        client = openai.OpenAI(base_url=model.base_url, api_key=model.api_key)
        try:
            stream = client.chat.completions.create(
                model=model.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                # DeepSeek thinking
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    yield {"type": "thinking", "data": delta.reasoning_content}
                elif delta.content:
                    yield {"type": "content", "data": delta.content}
        except Exception as e:
            yield {"type": "content", "data": f"\n\n❌ 流式调用失败: {e}"}

    def _stream_anthropic(self, model: ModelConfig, messages: list[dict], **kwargs):
        try:
            import anthropic
        except ImportError:
            yield {"type": "content", "data": "❌ 未安装 anthropic 库"}
            return

        client = anthropic.Anthropic(api_key=model.api_key)
        try:
            system_msg = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append(msg)

            with client.messages.stream(
                model=model.model_name,
                max_tokens=kwargs.get("max_tokens", 4096),
                system=system_msg if system_msg else anthropic.NOT_GIVEN,
                messages=user_messages,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, 'thinking'):
                            yield {"type": "thinking", "data": event.delta.thinking}
                        elif hasattr(event.delta, 'text'):
                            yield {"type": "content", "data": event.delta.text}
        except Exception as e:
            yield {"type": "content", "data": f"\n\n❌ 流式调用失败: {e}"}

    def _resolve_model(self, model_id: str | None, purpose: str) -> ModelConfig | None:
        if model_id and model_id in self._models:
            return self._models[model_id]
        return self.get_model(purpose)
