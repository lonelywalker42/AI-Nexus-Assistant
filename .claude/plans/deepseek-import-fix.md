# DeepSeek 对话导入功能修复方案

## 问题总结

| 问题 | 根因 | 影响 |
|------|------|------|
| 部分会话导入失败 | `_clean_messages()` 过度过滤（<3字符、停用词） | 短对话被跳过 |
| 摘要生成失败 | AIRouter 不支持 `response_format=json_object`，JSON 解析失败率高 | LLM 返回非标准 JSON |
| 会话未集合管理 | ChatPage 无导入分组概念，`category="topic"` 无对应 UI | 导入会话散落在普通列表 |

## 修复方案

### 1. 修复会话导入失败 (`deepseek_import_service.py`)

**改动**: 放宽消息过滤阈值

```python
# 当前
_SHORT_THRESHOLD = 3
_STOP_WORDS = {"继续", "好的", "嗯", "哦", "好", "是的", "对", "ok", "okay", "yes", "no"}

# 修改为
_SHORT_THRESHOLD = 1  # 允许单字符消息
_STOP_WORDS = {"继续", "好的", "嗯", "哦"}  # 缩小停用词范围
```

同时增加 fallback：如果清洗后消息数 < 2，保留原始消息中最长的几条。

### 2. 修复摘要生成失败

**方案A (推荐)**: 在 AIRouter 中添加 `response_format` 支持

**文件**: `app/ai/router.py`

在 `_call_openai()` 方法中传递 `response_format`:

```python
# 第 101-103 行附近
response = client.chat.completions.create(
    model=model.model_name,
    messages=messages,
    temperature=kwargs.get("temperature", 0.7),
    max_tokens=kwargs.get("max_tokens", 4096),
    response_format=kwargs.get("response_format"),  # 新增
)
```

**文件**: `app/services/deepseek_import_service.py`

修改 `_call_llm()` 使用 `response_format`:

```python
result = router.chat(messages, purpose="summary", temperature=temperature,
                     max_tokens=4096, response_format={"type": "json_object"})
```

**方案B (备选)**: 直接使用 OpenAI 客户端（参考 DeepseekManager 的做法）

在 `deepseek_import_service.py` 中直接创建 OpenAI 客户端调用，绕过 AIRouter。

### 3. 修复会话页面集合管理

**改动1**: 给 ChatSession 添加 `import_group_id` 字段

**文件**: `app/models/chat.py`

```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    # ... existing fields ...
    import_group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("import_groups.id", ondelete="SET NULL"), nullable=True
    )
```

**改动2**: 导入时设置 `import_group_id`

**文件**: `app/services/deepseek_import_service.py` 第 344-348 行

```python
chat_session = ChatSession(
    title=f"[导入] {title}",
    category="import",  # 改为 import 分类
    model_name="deepseek-import",
    import_group_id=group_id,  # 新增
)
```

**改动3**: ChatPage 添加 "导入" 分类

**文件**: `nexus-ui/src/pages/ChatPage.tsx`

```typescript
const CHAT_CATEGORIES = [
  { key: "all", label: "全部" },
  { key: "general", label: "通用" },
  { key: "review", label: "文献综述" },
  { key: "idea", label: "IDEA" },
  { key: "research", label: "研究" },
  { key: "discussion", label: "选题讨论" },
  { key: "import", label: "📥 导入" },  // 新增
];
```

**改动4**: ChatPage 左侧会话列表支持按 import_group 分组显示

当分类为 "import" 时，按 `import_group_id` 分组显示，类似 KnowledgePage 的导入分组视图。

**改动5**: API 端点支持

**文件**: `server.py`

在 `GET /api/chat/sessions` 响应中添加 `import_group_id` 字段。

在 `app/models/chat.py` 中添加 `import_group_id` 后，`chat_service.py` 的查询需要包含该字段。

### 4. 数据库迁移处理

由于项目使用 `create_all()` 而非 Alembic，新列不会自动添加到已有表。

**文件**: `app/db.py` 的 `init_db()` 函数

添加列存在性检查：

```python
def init_db():
    """创建所有表 + FTS5 索引 + 增量迁移"""
    import app.models
    Base.metadata.create_all(bind=engine)

    # 增量迁移: 添加缺失列
    _migrate_columns()

# ...

def _migrate_columns():
    """检查并添加缺失的列"""
    import sqlite3
    db_path = get_data_dir() / 'nexus.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 检查 chat_sessions 是否有 import_group_id
    cursor.execute("PRAGMA table_info(chat_sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'import_group_id' not in columns:
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN import_group_id TEXT REFERENCES import_groups(id) ON DELETE SET NULL")
        conn.commit()

    conn.close()
```

## 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `app/ai/router.py` | 添加 response_format 支持 |
| `app/services/deepseek_import_service.py` | 放宽过滤 + 使用 response_format |
| `app/models/chat.py` | 添加 import_group_id 字段 |
| `app/services/chat_service.py` | 查询包含 import_group_id |
| `server.py` | API 响应包含 import_group_id |
| `nexus-ui/src/api/client.ts` | ChatSession 类型添加 import_group_id |
| `nexus-ui/src/pages/ChatPage.tsx` | 添加导入分类 + 分组显示 |

## 实施顺序

1. AIRouter 添加 response_format 支持
2. deepseek_import_service 放宽过滤 + 使用 response_format
3. ChatSession 模型添加 import_group_id
4. 导入时设置 import_group_id
5. ChatPage 添加导入分类和分组显示
6. 测试验证
