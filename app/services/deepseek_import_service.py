"""DeepSeek 对话导入服务 — JSON 解析 + LLM pipeline + 知识卡片生成

参考 DeepseekManager 的 pipeline 架构，适配本项目的模型和服务层。
LLM 调用使用信号量限制并发数（默认最大 20）。
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

_MAX_CONCURRENT = 20
_llm_semaphore = Semaphore(_MAX_CONCURRENT)
_llm_executor = ThreadPoolExecutor(max_workers=_MAX_CONCURRENT, thread_name_prefix="llm-import")


def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """调用 LLM，受信号量限制并发数。使用 AIRouter 的同步 chat 接口。"""
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
        result = router.chat(messages, purpose="summary", temperature=temperature, max_tokens=4096)
        content = result.get("content", "")
        if content.startswith("[ERROR]"):
            raise RuntimeError(content)
        return content
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
_SHORT_THRESHOLD = 3
_STOP_WORDS = {"继续", "好的", "嗯", "哦", "好", "是的", "对", "ok", "okay", "yes", "no"}


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
    merged = _merge_consecutive(cleaned)
    text = _format_for_llm(merged)
    return merged, text


# ══════════════════════════════════════════════════════════════
#  LLM 操作
# ══════════════════════════════════════════════════════════════

def summarize_session(conversation_text: str) -> dict:
    """LLM 调用: 生成会话摘要"""
    system = "你是一个专业的个人知识管理助手。请分析以下对话，返回 JSON 格式的会话摘要。"
    user = f"""请分析这段对话并返回 JSON：

{{
  "session_title": "优化后的对话标题（简洁准确）",
  "overall_summary": "此对话整体讨论了什么，得到了哪些结论（2-3句话）",
  "knowledge_domain": ["领域1", "领域2"]
}}

对话内容：
{conversation_text}"""
    result = _call_llm(system, user)
    return _extract_json(result)


def split_topics(conversation_text: str, messages: list[dict]) -> list[dict]:
    """LLM 调用: 按语义话题切分对话"""
    system = "你是一个专业的对话分析助手。请将对话按语义话题切分，返回 JSON 格式的话题列表。"

    indexed_text = ""
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown").upper()
        indexed_text += f"[{i}][{role}]: {msg.get('content', '')}\n\n"

    user = f"""请将以下对话按话题切分，返回 JSON 数组：

[
  {{
    "topic_title": "话题标题",
    "start_msg_index": 0,
    "end_msg_index": 5,
    "brief": "此话题讨论了什么（一句话）"
  }}
]

注意：
- 每个话题应该是一个语义完整的讨论单元
- 话题之间不应重叠
- end_msg_index 是包含的（闭区间）
- 确保覆盖所有消息

对话内容（带索引）：
{indexed_text}"""

    result = _call_llm(system, user)
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        return parsed.get("topics", parsed.get("segments", []))
    return parsed


def generate_card(segment_text: str, topic_title: str) -> dict:
    """LLM 调用: 从话题片段生成知识卡片"""
    system = "你是一个专业的知识提炼助手。请从对话片段中提取结构化知识，返回 JSON 格式的知识卡片。"
    user = f"""请从以下对话片段中提取知识，返回 JSON：

{{
  "title": "知识卡片标题",
  "summary": "一句话概括核心知识点",
  "key_points": ["要点1", "要点2", "要点3"],
  "code_snippets": ["代码片段1（如有）"],
  "difficulty": "初级/中级/高级",
  "suggested_tags": ["标签1", "标签2", "标签3"],
  "suggested_category": "领域 > 子领域 > 细分"
}}

注意：
- key_points 提取 3-5 个核心要点
- code_snippets 保留原始格式，标注语言
- suggested_tags 提取 3-5 个关键词标签
- difficulty 根据内容复杂度判断

话题：{topic_title}

对话内容：
{segment_text}"""

    result = _call_llm(system, user)
    return _extract_json(result)


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


# ══════════════════════════════════════════════════════════════
#  Pipeline 编排
# ══════════════════════════════════════════════════════════════

def _update_group(db: Session, group_id: str, **kwargs):
    """更新 ImportGroup 字段"""
    group = db.get(ImportGroup, group_id)
    if group:
        for k, v in kwargs.items():
            if hasattr(group, k):
                setattr(group, k, v)
        db.commit()


def process_single_conversation(
    db: Session,
    group_id: str,
    conv: dict,
    index: int,
    total: int,
) -> dict:
    """处理单个对话的完整 pipeline

    1. 预处理消息
    2. 创建 ChatSession + 写入消息
    3. LLM 会话摘要
    4. LLM 话题切分
    5. 逐话题生成知识卡片
    6. 标签归一化
    """
    title = conv["title"]
    messages = conv["messages"]
    source_url = conv.get("source_url")

    _update_group(db, group_id, progress=f"[{index + 1}/{total}] 预处理: {title}")

    # ── Step 1: 预处理 ──
    cleaned_msgs, conversation_text = preprocess(messages)

    if not cleaned_msgs:
        return {"title": title, "cards": 0, "error": "预处理后无有效消息"}

    # ── Step 2: 创建 ChatSession 重建原始对话 ──
    _update_group(db, group_id, progress=f"[{index + 1}/{total}] 重建对话: {title}")

    chat_session = ChatSession(
        title=f"[导入] {title}",
        category="topic",
        model_name="deepseek-import",
    )
    db.add(chat_session)
    db.flush()

    # 写入原始消息
    for msg in cleaned_msgs:
        db.add(ChatMessage(
            session_id=chat_session.id,
            role=msg["role"],
            content=msg["content"],
        ))
    db.flush()

    # ── Step 3: LLM 会话摘要 ──
    _update_group(db, group_id, progress=f"[{index + 1}/{total}] 生成摘要: {title}")

    try:
        summary_data = summarize_session(conversation_text)
    except Exception as e:
        logger.error("会话摘要失败: %s", e)
        summary_data = {
            "session_title": title,
            "overall_summary": "摘要生成失败",
            "knowledge_domain": [],
        }

    # 更新会话标题为 LLM 优化后的标题
    optimized_title = summary_data.get("session_title", title)
    chat_session.title = f"[导入] {optimized_title}"
    db.flush()

    # ── Step 4: LLM 话题切分 ──
    _update_group(db, group_id, progress=f"[{index + 1}/{total}] 切分话题: {title}")

    try:
        topics = split_topics(conversation_text, cleaned_msgs)
    except Exception as e:
        logger.error("话题切分失败: %s", e)
        topics = [{
            "topic_title": optimized_title,
            "start_msg_index": 0,
            "end_msg_index": len(cleaned_msgs) - 1,
            "brief": summary_data.get("overall_summary", ""),
        }]

    if not topics:
        topics = [{
            "topic_title": optimized_title,
            "start_msg_index": 0,
            "end_msg_index": len(cleaned_msgs) - 1,
            "brief": summary_data.get("overall_summary", ""),
        }]

    # ── Step 5: 逐话题生成知识卡片 ──
    existing_tags = [t.name for t in db.query(Tag).all()]
    cards_created = 0

    for ti, topic in enumerate(topics):
        _update_group(db, group_id,
                      progress=f"[{index + 1}/{total}] 生成卡片 ({ti + 1}/{len(topics)}): {topic.get('topic_title', '')}")

        start_idx = topic.get("start_msg_index", 0)
        end_idx = topic.get("end_msg_index", len(cleaned_msgs) - 1)
        segment_msgs = cleaned_msgs[start_idx:end_idx + 1]
        segment_text = _format_for_llm(segment_msgs)
        topic_title = topic.get("topic_title", f"话题 {ti + 1}")

        # LLM 生成卡片
        try:
            card_data = generate_card(segment_text, topic_title)
        except Exception as e:
            logger.error("卡片生成失败 topic=%s: %s", topic_title, e)
            card_data = {
                "title": topic_title,
                "summary": topic.get("brief", ""),
                "key_points": [],
                "code_snippets": [],
                "difficulty": "未知",
                "suggested_tags": [],
                "suggested_category": "",
            }

        # 创建 KnowledgeCard
        card = KnowledgeCard(
            title=card_data.get("title", topic_title)[:200],
            summary=card_data.get("summary", "")[:1000],
            key_points=json.dumps(card_data.get("key_points", []), ensure_ascii=False),
            source_type="deepseek",
            import_group_id=group_id,
            chat_session_id=chat_session.id,
            category_path=card_data.get("suggested_category", ""),
            user_notes=f"source_url:{source_url}" if source_url else "",
        )
        db.add(card)
        db.flush()

        # ── Step 6: 标签归一化 ──
        suggested_tags = card_data.get("suggested_tags", [])
        seen_tags = set()
        tag_count = 0

        for tag_name in suggested_tags:
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
                tag = Tag(name=final_name, status="suggested", usage_count=1)
                db.add(tag)
                existing_tags.append(final_name)
            db.add(CardTag(card_id=card.id, tag_name=final_name))
            tag_count += 1

        cards_created += 1

    db.commit()

    return {
        "title": optimized_title,
        "chat_session_id": chat_session.id,
        "cards": cards_created,
        "topics": len(topics),
    }


def process_import(db: Session, group_id: str, conversations: list[dict]) -> dict:
    """完整导入 pipeline — 处理所有对话

    顺序处理每个对话（每个对话内部的 LLM 调用受信号量限制并发）。
    """
    total = len(conversations)
    _update_group(db, group_id, progress=f"开始处理 {total} 个对话...")

    all_results = []
    total_cards = 0
    errors = []

    for i, conv in enumerate(conversations):
        try:
            result = process_single_conversation(db, group_id, conv, i, total)
            all_results.append(result)
            total_cards += result.get("cards", 0)
        except Exception as e:
            logger.error("对话处理失败 [%d/%d] %s: %s", i + 1, total, conv.get("title", ""), e)
            errors.append(f"{conv.get('title', '未知')}: {e}")
            all_results.append({"title": conv.get("title", ""), "cards": 0, "error": str(e)})

    # 更新分组状态
    domain_set = set()
    for r in all_results:
        # 收集领域（从 summary_data 中）
        pass

    status = "completed" if not errors else "completed"
    error_text = "; ".join(errors) if errors else ""

    _update_group(db, group_id,
                  card_count=total_cards,
                  status=status,
                  error=error_text,
                  progress=f"完成！共生成 {total_cards} 张知识卡片" + (f"，{len(errors)} 个对话出错" if errors else ""))

    return {
        "group_id": group_id,
        "conversations": len(all_results),
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
    3. 调用 process_import
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

    # 执行 pipeline
    try:
        result = process_import(db, group.id, conversations)
        return {"group_id": group.id, **result}
    except Exception as e:
        logger.error("导入失败: %s", e)
        _update_group(db, group.id, status="failed", error=str(e))
        return {"group_id": group.id, "error": str(e)}
