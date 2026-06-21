"""统一 AI 服务层 — 支持 OpenAI 和 Anthropic 协议，处理 thinking 内容，支持工具调用

工具调用流程：
1. 模型生成文本 + 工具调用 → 执行工具 → 将结果送回模型
2. 中间轮次的文本不发送给前端（避免显示"让我搜索..."）
3. 仅最后一轮（无工具调用）的文本作为最终回复
4. 中间文本保留在消息历史中，确保模型看到自己的推理上下文
"""

import json
from typing import Generator
from app.db import get_session
from app.models.model_config import ModelConfig
from app.ai.web_search import (
    TOOL_DEFINITION_OPENAI, TOOL_DEFINITION_ANTHROPIC,
    execute_tool_call, is_search_error,
)
from app.ai.tools import (
    init_tools, get_all_openai_tools, get_all_anthropic_tools,
    execute_tool as execute_registered_tool,
)


class AIRouter:
    """统一 AI 服务层"""

    MAX_TOOL_ROUNDS = 3

    def __init__(self):
        self._models: dict[str, ModelConfig] = {}
        self._load_models()
        try:
            init_tools()
        except Exception as e:
            print(f"[AIRouter] Tool init warning: {e}", flush=True)
        self._openai_tools = [TOOL_DEFINITION_OPENAI] + get_all_openai_tools()
        self._anthropic_tools = [TOOL_DEFINITION_ANTHROPIC] + get_all_anthropic_tools()

    def _load_models(self):
        db = get_session()
        try:
            models = db.query(ModelConfig).filter(ModelConfig.is_active == True).all()
            self._models = {m.id: m for m in models}
        finally:
            db.close()

    def reload(self):
        self._load_models()

    def get_model(self, purpose: str = "all") -> ModelConfig | None:
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
        try:
            import openai
        except ImportError as e:
            return {"thinking": "", "content": f"❌ 未安装 openai 库: {e}"}
        except Exception as e:
            return {"thinking": "", "content": f"❌ openai 导入异常: {type(e).__name__}: {e}"}

        # 确保 base_url 以 /v1 结尾
        base_url = model.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"

        print(f"[router] Calling OpenAI API: base_url={base_url}, model={model.model_name}", flush=True)

        client = openai.OpenAI(base_url=base_url, api_key=model.api_key)
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
            print(f"[router] API call succeeded, content length={len(content)}", flush=True)
            return {"thinking": thinking, "content": content}
        except openai.NotFoundError as e:
            error_msg = f"❌ API 端点不存在 (404): base_url={base_url}, model={model.model_name}。请检查配置。错误: {e}"
            print(f"[router] {error_msg}", flush=True)
            return {"thinking": "", "content": error_msg}
        except openai.AuthenticationError as e:
            error_msg = f"❌ API 认证失败 (401): 请检查 API Key。错误: {e}"
            print(f"[router] {error_msg}", flush=True)
            return {"thinking": "", "content": error_msg}
        except Exception as e:
            error_msg = f"❌ AI 调用失败: {type(e).__name__}: {e}"
            print(f"[router] {error_msg}", flush=True)
            return {"thinking": "", "content": error_msg}

    def _call_anthropic(self, model: ModelConfig, messages: list[dict], **kwargs) -> dict:
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
        """OpenAI 协议流式调用，支持工具调用循环

        关键逻辑：
        - 每轮收集文本内容和工具调用
        - 工具调用轮次：文本存入历史但不 yield 给前端
        - 最终轮次（无工具调用）：文本 yield 给前端
        """
        try:
            import openai
        except ImportError as e:
            yield {"type": "content", "data": f"❌ 未安装 openai 库: {e}"}
            return
        except Exception as e:
            yield {"type": "content", "data": f"❌ openai 导入异常: {type(e).__name__}: {e}"}
            return

        # 确保 base_url 以 /v1 结尾
        base_url = model.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"

        client = openai.OpenAI(base_url=base_url, api_key=model.api_key)
        current_messages = list(messages)

        for round_num in range(self.MAX_TOOL_ROUNDS + 1):
            try:
                print(f"[router] round {round_num}: calling API with {len(current_messages)} msgs, "
                      f"model={model.model_name}", flush=True)
                stream = client.chat.completions.create(
                    model=model.model_name,
                    messages=current_messages,
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 4096),
                    tools=self._openai_tools,
                    tool_choice="auto",
                    stream=True,
                )
                print(f"[router] round {round_num}: API call succeeded, streaming...", flush=True)

                tool_calls = {}
                has_tool_call = False
                text_content = ""  # 本轮文本内容（存入历史）
                round_thinking = ""  # 本轮思考内容（暂存，确认无工具调用后才 yield）
                chunk_count = 0

                for chunk in stream:
                    chunk_count += 1
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    # thinking（DeepSeek reasoning_content）— 暂存，不在工具调用轮次 yield
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        round_thinking += delta.reasoning_content

                    # 文本内容 — 收集但暂不 yield（等确认无工具调用后再决定）
                    if delta.content:
                        text_content += delta.content

                    # 工具调用
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

                print(f"[router] round {round_num}: stream done, "
                      f"chunks={chunk_count}, has_tool={has_tool_call}, "
                      f"text={len(text_content)} chars, thinking={len(round_thinking)} chars",
                      flush=True)

                if not has_tool_call or round_num == self.MAX_TOOL_ROUNDS:
                    # 最终轮次（无工具调用 或 已达最大轮次）— yield thinking 和文本内容
                    if not text_content and round_num == self.MAX_TOOL_ROUNDS:
                        # 模型用完所有轮次仍在调用工具 — 强制请求最终回复
                        print(f"[router] max tool rounds reached, forcing final response", flush=True)
                        current_messages.append({
                            "role": "user",
                            "content": "请基于以上所有搜索结果和信息，直接回答用户的问题。不需要再搜索。"
                        })
                        try:
                            final_stream = client.chat.completions.create(
                                model=model.model_name,
                                messages=current_messages,
                                temperature=kwargs.get("temperature", 0.7),
                                max_tokens=kwargs.get("max_tokens", 4096),
                                stream=True,
                            )
                            for chunk in final_stream:
                                if not chunk.choices:
                                    continue
                                delta = chunk.choices[0].delta
                                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                                    yield {"type": "thinking", "data": delta.reasoning_content}
                                if delta.content:
                                    text_content += delta.content
                                    yield {"type": "content", "data": delta.content}
                        except Exception as e:
                            print(f"[router] forced final response error: {e}", flush=True)
                    else:
                        if round_thinking:
                            yield {"type": "thinking", "data": round_thinking}
                        if text_content:
                            yield {"type": "content", "data": text_content}
                    return

                # 工具调用轮次
                # 1. 执行所有工具，收集结果
                tool_calls_for_msg = []
                tool_results_for_msg = []
                for idx in sorted(tool_calls.keys()):
                    tc = tool_calls[idx]
                    tool_name = tc["name"]

                    try:
                        args = json.loads(tc["arguments"])
                        query = args.get("query", args.get("q", ""))
                    except (json.JSONDecodeError, KeyError):
                        query = ""

                    yield {"type": "tool_call", "data": json.dumps({
                        "name": tool_name, "query": query
                    }, ensure_ascii=False)}

                    if tool_name == "web_search":
                        result = execute_tool_call(tc["arguments"])
                    else:
                        result = execute_registered_tool(tool_name, tc["arguments"])

                    yield {"type": "tool_result", "data": json.dumps({
                        "name": tool_name, "query": query, "result": result[:5000]
                    }, ensure_ascii=False)}

                    # 搜索服务不可用时短路，避免浪费工具调用轮次
                    if tool_name == "web_search" and is_search_error(result):
                        # 构建完整的消息历史
                        all_tool_calls = tool_calls_for_msg + [{
                            "id": tc["id"], "type": "function",
                            "function": {"name": tool_name, "arguments": tc["arguments"]}
                        }]
                        current_messages.append({
                            "role": "assistant",
                            "content": text_content if text_content else "",
                            "tool_calls": all_tool_calls,
                        })
                        current_messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                        current_messages.append({
                            "role": "user",
                            "content": "搜索服务暂时不可用。请直接基于你的知识回答用户的问题，不要尝试搜索。"
                        })
                        # 发起不带 tools 的最终调用
                        try:
                            final_stream = client.chat.completions.create(
                                model=model.model_name, messages=current_messages,
                                temperature=kwargs.get("temperature", 0.7),
                                max_tokens=kwargs.get("max_tokens", 4096), stream=True,
                            )
                            for chunk in final_stream:
                                if not chunk.choices: continue
                                delta = chunk.choices[0].delta
                                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                                    yield {"type": "thinking", "data": delta.reasoning_content}
                                if delta.content:
                                    yield {"type": "content", "data": delta.content}
                        except Exception as e:
                            yield {"type": "content", "data": f"\n\n❌ {e}"}
                        return

                    tool_calls_for_msg.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tc["arguments"],
                        }
                    })
                    tool_results_for_msg.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                # 2. 追加消息：assistant(text + tool_calls) → tool(results)
                #    OpenAI 格式：一个 assistant 消息包含 content + tool_calls，后面跟 tool 消息
                #    兼容 DeepSeek 等国产模型：content 使用空字符串而非 null
                current_messages.append({
                    "role": "assistant",
                    "content": text_content if text_content else "",
                    "tool_calls": tool_calls_for_msg,
                })
                current_messages.extend(tool_results_for_msg)

                print(f"[router] round {round_num}: executed {len(tool_calls_for_msg)} tool(s), "
                      f"msg_history={len(current_messages)} msgs", flush=True)
                # 打印最后几条消息的角色和长度，方便调试
                for i, m in enumerate(current_messages[-4:]):
                    role = m.get("role", "?")
                    clen = len(str(m.get("content", "")))
                    has_tc = "tool_calls" in m and m["tool_calls"]
                    print(f"[router]   msg[{len(current_messages)-4+i}]: role={role}, "
                          f"content={clen}chars, tool_calls={has_tc}", flush=True)

            except Exception as e:
                import traceback
                print(f"[router] round {round_num} exception: {e}", flush=True)
                traceback.print_exc()
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
                    tools=self._anthropic_tools,
                ) as stream:
                    tool_use_blocks = []
                    current_tool_id = None
                    current_tool_name = None
                    current_tool_input = ""
                    in_tool_use = False
                    text_content = ""
                    round_thinking = ""

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
                                round_thinking += event.delta.thinking
                            elif hasattr(event.delta, 'text'):
                                text_content += event.delta.text
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

                if not tool_use_blocks:
                    # 最终轮次 — yield thinking 和文本
                    if round_thinking:
                        yield {"type": "thinking", "data": round_thinking}
                    if text_content:
                        yield {"type": "content", "data": text_content}
                    return

                # 工具调用轮次 — 文本存入历史但不 yield
                assistant_content = []
                if text_content:
                    assistant_content.append({"type": "text", "text": text_content})

                tool_results = []
                for tu in tool_use_blocks:
                    tool_name = tu["name"]

                    try:
                        args = json.loads(tu["input_json"])
                        query = args.get("query", args.get("q", ""))
                    except (json.JSONDecodeError, KeyError):
                        query = ""

                    yield {"type": "tool_call", "data": json.dumps({
                        "name": tool_name, "query": query
                    }, ensure_ascii=False)}

                    if tool_name == "web_search":
                        result = execute_tool_call(tu["input_json"])
                    else:
                        result = execute_registered_tool(tool_name, tu["input_json"])

                    yield {"type": "tool_result", "data": json.dumps({
                        "name": tool_name, "query": query, "result": result[:5000]
                    }, ensure_ascii=False)}

                    assistant_content.append({
                        "type": "tool_use",
                        "id": tu["id"],
                        "name": tu["name"],
                        "input": json.loads(tu["input_json"]),
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": result,
                    })

                current_messages.append({"role": "assistant", "content": assistant_content})
                current_messages.append({"role": "user", "content": tool_results})

            except Exception as e:
                import traceback
                print(f"[router] round {round_num} exception: {e}", flush=True)
                traceback.print_exc()
                yield {"type": "content", "data": f"\n\n❌ 流式调用失败: {e}"}
                return

    def _resolve_model(self, model_id: str | None, purpose: str) -> ModelConfig | None:
        if model_id and model_id in self._models:
            return self._models[model_id]
        return self.get_model(purpose)
