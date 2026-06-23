"""DeepSeek 对话导入服务 — JSON 解析 + LLM 摘要 + 知识卡片生成

两阶段 pipeline 架构：
  阶段 1: 解析 JSON → 预处理 → 批量保存完整会话（无 LLM 调用，快速持久化）
  阶段 2: 逐会话调用 LLM API 生成总结概要，每个会话生成一张知识卡片

LLM 调用使用信号量限制并发数（默认最大 5）。
"""

import json
import re
import uuid
import logging
from datetime import datetime
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeCard, Tag, CardTag
from app.models.chat import ChatSession, ChatMessage
from app.models.import_group import ImportGroup
from app.services import knowledge_service, chat_service

logger = logging.getLogger(__name__)

# ── LLM 并发控制 ─────────────────────────────────────────────

_MAX_CONCURRENT = 5
_llm_semaphore = Semaphore(_MAX_CONCURRENT)
_llm_executor = ThreadPoolExecutor(max_workers=_MAX_CONCURRENT, thread_name_prefix="llm-import")


def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 4096) -> str:
    """调用 LLM，受信号量限制并发数。使用 AIRouter 的同步 chat 接口。

    含重试逻辑：response_format 失败时自动去掉该参数重试。
    """
    # 截断过长的prompt，避免超出模型上下文窗口
    if len(user_prompt) > 12000:
        user_prompt = user_prompt[:12000] + "\n\n[内容过长已截断]"

    _llm_semaphore.acquire()
    try:
        from app.ai.router import AIRouter
        router = AIRouter()
        model = router.get_model(purpose="summary") or router.get_model()
        if not model:
            raise RuntimeError("未配置 AI 模型，请在设置中添加")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error = None
        # 先尝试带 response_format，失败则去掉重试
        for use_json_format in [True, False]:
            try:
                kwargs = {"temperature": temperature, "max_tokens": max_tokens}
                if use_json_format:
                    kwargs["response_format"] = {"type": "json_object"}
                result = router.chat(messages, purpose="summary", **kwargs)
                content = result.get("content", "")
                if content.startswith("[ERROR]"):
                    raise RuntimeError(content)
                return content
            except Exception as e:
                last_error = e
                if use_json_format:
                    logger.warning("JSON格式调用失败，尝试普通格式: %s", e)
                    continue
                raise

        raise last_error or RuntimeError("LLM调用失败")
    finally:
        _llm_semaphore.release()


def _extract_json(text: str) -> dict | list:
    """从 LLM 响应中提取 JSON（3 级 fallback）"""
    text = text.strip()
    # 1. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2. 从 ```json ``` 代码块提取
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 3. 查找第一个 { 或 [ 并匹配闭合
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"无法从 LLM 响应中提取 JSON: {text[:200]}...")


# ══════════════════════════════════════════════════════════════
#  JSON 解析
# ══════════════════════════════════════════════════════════════

def walk_mapping(mapping: dict, node_id: str) -> list[dict]:
    """DFS 遍历 DeepSeek mapping 树，提取消息列表"""
    node = mapping.get(node_id)
    if not node:
        return []
    messages = []
    msg = node.get("message")
    if msg and msg.get("fragments"):
        for frag in msg["fragments"]:
            content = frag.get("content", "")
            if not content:
                continue
            frag_type = frag.get("type", "")
            if frag_type == "REQUEST":
                messages.append({"role": "user", "content": content})
            elif frag_type == "RESPONSE":
                messages.append({"role": "assistant", "content": content})
            # THINK fragments 跳过
    for child_id in node.get("children", []):
        messages.extend(walk_mapping(mapping, child_id))
    return messages


def parse_deepseek_json(data: dict | list) -> list[dict]:
    """解析 DeepSeek 导出 JSON，返回对话列表。

    每个对话: {"title": str, "messages": list[dict], "source_url": str|None}
    支持 4 种格式:
    1. 对象数组（含 mapping 树）— 典型 DeepSeek 导出
    2. 单个对象（含 mapping 树）
    3. 简单 messages 数组
    4. 含 messages/conversation 键的对象
    """
    conversations = []

    # Case 1: 对象数组（含 mapping 树）
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "mapping" in data[0]:
        for conv in data:
            conv_id = conv.get("id", "")
            source_url = f"https://chat.deepseek.com/c/{conv_id}" if conv_id else None
            title = conv.get("title", "DeepSeek 对话")
            messages = walk_mapping(conv.get("mapping", {}), "root")
            if messages:
                conversations.append({"title": title, "messages": messages, "source_url": source_url})
        return conversations

    # Case 2: 单个对象（含 mapping 树）
    if isinstance(data, dict) and "mapping" in data:
        conv_id = data.get("id", "")
        source_url = f"https://chat.deepseek.com/c/{conv_id}" if conv_id else None
        title = data.get("title", "DeepSeek 对话")
        messages = walk_mapping(data["mapping"], "root")
        if messages:
            conversations.append({"title": title, "messages": messages, "source_url": source_url})
        return conversations

    # Case 3: 简单 messages 数组
    if isinstance(data, list):
        messages = []
        for item in data:
            if isinstance(item, dict) and "role" in item:
                messages.append({"role": item["role"], "content": item.get("content", "")})
        if messages:
            conversations.append({"title": "导入对话", "messages": messages, "source_url": None})
        return conversations

    # Case 4: 含 messages/conversation 键的对象
    if isinstance(data, dict):
        source_url = data.get("source_url") or data.get("url")
        msg_list = data.get("messages", data.get("conversation", []))
        title = data.get("title", "导入对话")
        if isinstance(msg_list, list):
            messages = []
            for item in msg_list:
                if isinstance(item, dict) and "role" in item:
                    messages.append({"role": item["role"], "content": item.get("content", "")})
            if messages:
                conversations.append({"title": title, "messages": messages, "source_url": source_url})

    return conversations


# ══════════════════════════════════════════════════════════════
#  消息预处理
# ══════════════════════════════════════════════════════════════

_EMOJI_ONLY = re.compile(
    r"^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F"
    r"\U0000200D\U00002640\U00002642\s]+$"
)
_SHORT_THRESHOLD = 1  # 允许单字符消息（如 "好"）
_STOP_WORDS = {"继续", "好的", "嗯", "哦"}  # 缩小停用词范围，保留更多有意义消息


def _clean_messages(messages: list[dict]) -> list[dict]:
    """清除无意义消息（纯 emoji、超短、停用词）"""
    cleaned = []
    for msg in messages:
        content = msg.get("content", "").strip()
        if not content or len(content) < _SHORT_THRESHOLD:
            continue
        if _EMOJI_ONLY.match(content):
            continue
        if content.lower() in _STOP_WORDS:
            continue
        cleaned.append({"role": msg["role"], "content": content})
    return cleaned


def _merge_consecutive(messages: list[dict]) -> list[dict]:
    """合并连续同角色消息"""
    if not messages:
        return []
    merged = [messages[0].copy()]
    for msg in messages[1:]:
        if msg["role"] == merged[-1]["role"]:
            merged[-1]["content"] += "\n\n" + msg["content"]
        else:
            merged.append(msg.copy())
    return merged


def _format_for_llm(messages: list[dict]) -> str:
    """格式化消息为 LLM 输入文本"""
    lines = []
    for msg in messages:
        role_label = {"user": "USER", "assistant": "ASSISTANT"}.get(msg["role"], msg["role"].upper())
        lines.append(f"[{role_label}]: {msg['content']}")
    return "\n\n".join(lines)


def preprocess(messages: list[dict]) -> tuple[list[dict], str]:
    """完整预处理流水线，返回 (清洗后消息, 格式化文本)"""
    cleaned = _clean_messages(messages)
    # 如果清洗后消息过少（<2条），保留原始消息中最长的几条作为 fallback
    if len(cleaned) < 2 and len(messages) >= 2:
        # 按内容长度排序，保留最长的消息
        sorted_msgs = sorted(messages, key=lambda m: len(m.get("content", "")), reverse=True)
        cleaned = [{"role": m["role"], "content": m["content"].strip()}
                   for m in sorted_msgs[:10] if m.get("content", "").strip()]
    merged = _merge_consecutive(cleaned)
    text = _format_for_llm(merged)
    return merged, text


# ══════════════════════════════════════════════════════════════
#  LLM 操作
# ══════════════════════════════════════════════════════════════

def summarize_session(conversation_text: str) -> dict:
    """LLM 调用: 生成会话摘要

    返回: {"session_title": str, "overall_summary": str, "knowledge_domain": [str]}
    """
    # 截断过长的对话文本（保留前10000字符）
    if len(conversation_text) > 10000:
        conversation_text = conversation_text[:10000] + "\n\n[对话过长已截断，以上为前部分内容]"

    system = "你是一个专业的个人知识管理助手。请分析以下对话，返回 JSON 格式的会话摘要。严格返回 JSON，不要包含其他文字。"
    user = f"""请分析这段对话并返回 JSON：

{{
  "session_title": "优化后的对话标题（简洁准确）",
  "overall_summary": "此对话整体讨论了什么，得到了哪些结论（2-3句话）",
  "knowledge_domain": ["领域1", "领域2"]
}}

对话内容：
{conversation_text}"""
    result = _call_llm(system, user)
    try:
        return _extract_json(result)
    except ValueError as e:
        logger.warning("会话摘要JSON解析失败，使用默认值: %s", e)
        return {
            "session_title": "",
            "overall_summary": result[:500] if result else "摘要生成失败",
            "knowledge_domain": [],
        }


# ══════════════════════════════════════════════════════════════
#  标签归一化
# ══════════════════════════════════════════════════════════════

def _find_similar_tag(tag_name: str, existing_tags: list[str], threshold: float = 0.7) -> str | None:
    """模糊匹配已有标签"""
    best_match = None
    best_score = 0
    for existing in existing_tags:
        score = SequenceMatcher(None, tag_name.lower(), existing.lower()).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = existing
    return best_match


def _create_card_tags(db: Session, card: KnowledgeCard, tag_names: list[str], existing_tags: list[str]):
    """为卡片创建标签关联（归一化去重，处理并发冲突）"""
    seen_tags = set()
    tag_count = 0
    for tag_name in tag_names:
        tag_name = tag_name.strip()
        if not tag_name or tag_count >= 5:
            continue
        matched = _find_similar_tag(tag_name, existing_tags)
        final_name = matched or tag_name
        if final_name.lower() in seen_tags:
            continue
        seen_tags.add(final_name.lower())

        tag = db.get(Tag, final_name)
        if tag:
            tag.usage_count = (tag.usage_count or 0) + 1
        else:
            try:
                tag = Tag(name=final_name, status="suggested", usage_count=1)
                db.add(tag)
                db.flush()  # 先flush确保Tag存在，捕获UNIQUE冲突
            except Exception:
                db.rollback()
                # 并发插入了相同Tag，重新获取
                tag = db.get(Tag, final_name)
                if tag:
                    tag.usage_count = (tag.usage_count or 0) + 1
                else:
                    continue  # 极端情况跳过
        db.add(CardTag(card_id=card.id, tag_name=final_name))
        tag_count += 1
        if final_name not in existing_tags:
            existing_tags.append(final_name)


# ══════════════════════════════════════════════════════════════
#  Pipeline 编排 — 两阶段架构
# ══════════════════════════════════════════════════════════════

def _update_group(db: Session, group_id: str, **kwargs):
    """更新 ImportGroup 字段"""
    group = db.get(ImportGroup, group_id)
    if group:
        for k, v in kwargs.items():
            if hasattr(group, k):
                setattr(group, k, v)
        db.commit()


# ── 阶段 1: 解析 & 保存完整会话（无 LLM 调用）──────────────────

def save_conversations(db: Session, group_id: str, conversations: list[dict]) -> list[dict]:
    """阶段 1: 解析 & 预处理 & 批量保存会话到数据库

    不调用任何 LLM API，仅做 JSON 解析、消息清洗、写入 ChatSession + ChatMessage。

    返回:
        session_infos: 每个会话的元数据列表
        [{"session_id": str, "title": str, "source_url": str|None,
          "cleaned_msgs": list[dict], "conversation_text": str}, ...]
    """
    total = len(conversations)
    session_infos = []

    for i, conv in enumerate(conversations):
        title = conv["title"]
        messages = conv["messages"]
        source_url = conv.get("source_url")

        _update_group(db, group_id, progress=f"[阶段1] 保存会话 [{i + 1}/{total}]: {title}")

        # 预处理（清洗 + 合并，不含 LLM）
        cleaned_msgs, conversation_text = preprocess(messages)

        if not cleaned_msgs:
            logger.warning("会话 '%s' 预处理后无有效消息，跳过", title)
            continue

        # 创建 ChatSession
        chat_session = ChatSession(
            title=f"[导入] {title}",
            category="import",
            model_name="deepseek-import",
            import_group_id=group_id,
        )
        db.add(chat_session)
        db.flush()

        # 写入消息
        for msg in cleaned_msgs:
            db.add(ChatMessage(
                session_id=chat_session.id,
                role=msg["role"],
                content=msg["content"],
            ))
        db.flush()

        session_infos.append({
            "session_id": chat_session.id,
            "title": title,
            "source_url": source_url,
            "cleaned_msgs": cleaned_msgs,
            "conversation_text": conversation_text,
        })

    db.commit()
    return session_infos


# ── 阶段 2: 逐会话 LLM 生成总结概要 ──────────────────────────

def _process_single_session_llm(
    db: Session,
    group_id: str,
    info: dict,
    index: int,
    total: int,
) -> dict:
    """对单个已保存的会话执行 LLM 总结

    每个会话生成一张知识卡片（整个会话的总结概要）。
    """
    session_id = info["session_id"]
    title = info["title"]
    source_url = info["source_url"]
    conversation_text = info["conversation_text"]

    chat_session = db.get(ChatSession, session_id)
    if not chat_session:
        return {"title": title, "cards": 0, "error": "会话记录不存在"}

    # ── LLM 生成总结概要 ──
    _update_group(db, group_id, progress=f"[阶段2] [{index + 1}/{total}] 生成概要: {title}")

    try:
        summary_data = summarize_session(conversation_text)
        logger.info("会话摘要成功 [%d/%d]: %s", index + 1, total, title)
    except Exception as e:
        logger.error("会话摘要失败 [%d/%d] %s: %s", index + 1, total, title, e, exc_info=True)
        summary_data = {
            "session_title": title,
            "overall_summary": f"摘要生成失败: {str(e)[:200]}",
            "knowledge_domain": [],
        }

    # 更新会话标题为 LLM 优化后的标题
    optimized_title = summary_data.get("session_title", title)
    chat_session.title = f"[导入] {optimized_title}"
    db.flush()

    # ── 创建知识卡片（一个会话 = 一张卡片）──
    _update_group(db, group_id, progress=f"[阶段2] [{index + 1}/{total}] 创建卡片: {optimized_title}")

    card = KnowledgeCard(
        title=optimized_title[:200],
        summary=summary_data.get("overall_summary", "")[:1000],
        key_points=json.dumps([], ensure_ascii=False),
        source_type="deepseek",
        import_group_id=group_id,
        chat_session_id=session_id,
        category_path=" > ".join(summary_data.get("knowledge_domain", [])),
        user_notes=f"source_url:{source_url}" if source_url else "",
    )
    db.add(card)
    db.flush()

    # 标签归一化（使用 knowledge_domain 作为标签）
    existing_tags = [t.name for t in db.query(Tag).all()]
    domain_tags = summary_data.get("knowledge_domain", [])
    if domain_tags:
        _create_card_tags(db, card, domain_tags, existing_tags)

    db.commit()

    return {
        "title": optimized_title,
        "session_id": session_id,
        "cards": 1,
        "summary": summary_data.get("overall_summary", ""),
        "knowledge_domain": summary_data.get("knowledge_domain", []),
    }


def _llm_batch_worker(args: tuple) -> dict:
    """线程池 worker: 处理单个会话的 LLM 总结

    注意: 每个 worker 创建独立的 DB session（线程安全）。
    """
    group_id, info, index, total = args
    db = None
    try:
        from app.db import get_session
        db = get_session()
        return _process_single_session_llm(db, group_id, info, index, total)
    except Exception as e:
        logger.error("LLM 处理失败 [%d/%d] %s: %s", index + 1, total, info.get("title", ""), e)
        return {"title": info.get("title", ""), "cards": 0, "error": str(e)}
    finally:
        if db:
            db.close()


def process_llm_batch(db: Session, group_id: str, session_infos: list[dict]) -> list[dict]:
    """阶段 2: 批量 LLM 处理所有已保存的会话

    使用线程池并发处理（受信号量限制最大 5 并发 LLM 调用）。
    """
    total = len(session_infos)
    if total == 0:
        return []

    _update_group(db, group_id, progress=f"[阶段2] 开始 LLM 处理 {total} 个会话...")

    # 提交所有任务到线程池
    futures = []
    for i, info in enumerate(session_infos):
        future = _llm_executor.submit(_llm_batch_worker, (group_id, info, i, total))
        futures.append(future)

    # 收集结果
    results = []
    for future in as_completed(futures):
        try:
            result = future.result()
            results.append(result)
        except Exception as e:
            logger.error("LLM 批处理异常: %s", e)
            results.append({"title": "未知", "cards": 0, "error": str(e)})

    return results


# ── 主 pipeline 编排 ─────────────────────────────────────────

def process_import(db: Session, group_id: str, conversations: list[dict]) -> dict:
    """完整导入 pipeline — 两阶段架构

    阶段 1: 解析 → 预处理 → 批量保存完整会话（无 LLM）
    阶段 2: 逐会话调用 LLM 生成总结概要 → 创建知识卡片（一个会话一张卡片）
    """
    total = len(conversations)
    _update_group(db, group_id, progress=f"开始处理 {total} 个对话...")

    # ═══ 阶段 1: 保存完整会话 ═══
    session_infos = save_conversations(db, group_id, conversations)

    if not session_infos:
        _update_group(db, group_id, status="failed", error="所有会话预处理后无有效消息")
        return {"group_id": group_id, "conversations": 0, "total_cards": 0, "errors": ["无有效消息"]}

    _update_group(db, group_id,
                  progress=f"[阶段1] 完成！已保存 {len(session_infos)} 个会话，开始生成概要...")

    # ═══ 阶段 2: 逐会话 LLM 生成概要 ═══
    llm_results = process_llm_batch(db, group_id, session_infos)

    # 汇总结果
    total_cards = 0
    errors = []
    domain_set = set()
    summaries = []

    for r in llm_results:
        total_cards += r.get("cards", 0)
        if r.get("error"):
            errors.append(f"{r.get('title', '未知')}: {r['error']}")
        for d in r.get("knowledge_domain", []):
            domain_set.add(d)
        if r.get("summary"):
            summaries.append(r["summary"])

    # 更新分组最终状态
    group_summary = "；".join(summaries[:5]) if summaries else ""
    error_text = "; ".join(errors) if errors else ""

    # 判断是否全部失败
    if total_cards == 0 and errors:
        status = "failed"
        progress_msg = f"所有 {len(errors)} 个会话的摘要生成均失败"
    else:
        status = "completed"
        progress_msg = (f"完成！共生成 {total_cards} 张知识卡片"
                        + (f"，{len(errors)} 个会话出错" if errors else ""))

    _update_group(db, group_id,
                  card_count=total_cards,
                  summary=group_summary[:2000],
                  knowledge_domain=json.dumps(list(domain_set), ensure_ascii=False),
                  status=status,
                  error=error_text[:2000] if error_text else "",
                  progress=progress_msg)

    return {
        "group_id": group_id,
        "conversations": len(session_infos),
        "total_cards": total_cards,
        "errors": errors,
    }


# ══════════════════════════════════════════════════════════════
#  入口函数
# ══════════════════════════════════════════════════════════════

def start_import(db: Session, data: dict | list, filename: str = "") -> dict:
    """启动导入流程（同步调用，由 BackgroundTask 包装）

    1. 解析 JSON
    2. 创建 ImportGroup
    3. 两阶段 pipeline: 保存会话 → 逐个生成总结概要
    """
    conversations = parse_deepseek_json(data)
    if not conversations:
        return {"error": "未能从 JSON 中解析出有效对话"}

    total_messages = sum(len(c["messages"]) for c in conversations)

    # 创建导入分组
    group = ImportGroup(
        title=conversations[0]["title"] if len(conversations) == 1 else f"批量导入 ({len(conversations)} 个对话)",
        source_url=conversations[0].get("source_url") or "",
        source_type="deepseek",
        original_filename=filename,
        message_count=total_messages,
        status="processing",
        progress=f"已解析 {len(conversations)} 个对话，共 {total_messages} 条消息",
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    # 执行两阶段 pipeline
    try:
        result = process_import(db, group.id, conversations)
        return {"group_id": group.id, **result}
    except Exception as e:
        logger.error("导入失败: %s", e)
        _update_group(db, group.id, status="failed", error=str(e))
        return {"group_id": group.id, "error": str(e)}
