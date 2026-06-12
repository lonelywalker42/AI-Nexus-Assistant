"""文献管理页面 — 5 个 Tab：关键词检索 / 标题检索 / AI综述 / 选题讨论 / 历史记录

渲染方式（参照 ai-literature）：
- AI综述: Markdown 渲染 (QTextBrowser.setMarkdown)
- 选题讨论: JSON 美化 + 语法高亮
- 历史记录: 支持重载（点击重新执行搜索/查看综述/查看选题）
"""

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QTextBrowser, QTabWidget, QScrollArea, QFrame,
    QCheckBox, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSizePolicy, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from app.ui.theme import (
    get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, BTN_GHOST_QSS,
    INPUT_QSS, COMBO_QSS, TABLE_QSS, TAB_QSS, SCROLLBAR_QSS, RADIUS,
)
from app.ui.widgets.paper_card import PaperCard
from app.db import get_session
from app.models.search_history import SearchHistory


class _SearchWorker(QThread):
    """后台搜索线程"""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, engine, query, sources, max_results):
        super().__init__()
        self._engine = engine
        self._query = query
        self._sources = sources
        self._max_results = max_results

    def run(self):
        try:
            results = self._engine.search(
                self._query, sources=self._sources, max_results=self._max_results
            )
            self.finished.emit([p.to_dict() for p in results])
        except Exception as e:
            self.error.emit(str(e))


class _ReviewWorker(QThread):
    """AI 综述生成线程（流式）"""
    chunk = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, ai_router, messages):
        super().__init__()
        self._router = ai_router
        self._messages = messages

    def run(self):
        try:
            full = ""
            for c in self._router.stream_chat(self._messages, purpose="review"):
                if c["type"] == "content":
                    full += c["data"]
                    self.chunk.emit(c["data"])
            self.finished.emit(full)
        except Exception as e:
            self.error.emit(str(e))


class LiteraturePage(QWidget):
    """文献管理页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._results: list[dict] = []
        self._search_engine = None
        self._worker = None
        self._review_worker = None
        self._current_query: str = ""
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_QSS())

        self._tabs.addTab(self._build_keyword_tab(), "关键词检索")
        self._tabs.addTab(self._build_title_tab(), "标题检索")
        self._tabs.addTab(self._build_review_tab(), "AI 综述")
        self._tabs.addTab(self._build_topic_tab(), "选题讨论")
        self._tabs.addTab(self._build_history_tab(), "历史记录")

        layout.addWidget(self._tabs)

    def refresh(self):
        self._load_history()

    def reapply_theme(self):
        self._theme = get_theme()

    # ── Tab 1: 关键词检索 ────────────────────────────────────

    def _build_keyword_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        kw_label = QLabel("关键词组（组内 AND，组间 OR）:")
        kw_label.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        layout.addWidget(kw_label)

        self._kw_container = QWidget()
        self._kw_layout = QVBoxLayout(self._kw_container)
        self._kw_layout.setContentsMargins(0, 0, 0, 0)
        self._kw_layout.setSpacing(8)
        layout.addWidget(self._kw_container)

        kw_btn_row = QHBoxLayout()
        add_group_btn = QPushButton("添加 OR 组")
        add_group_btn.setStyleSheet(BTN_SECONDARY_QSS())
        add_group_btn.clicked.connect(self._add_kw_group)
        kw_btn_row.addWidget(add_group_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(BTN_SECONDARY_QSS())
        clear_btn.clicked.connect(self._clear_kw_groups)
        kw_btn_row.addWidget(clear_btn)
        kw_btn_row.addStretch()
        layout.addLayout(kw_btn_row)

        sources_row = QHBoxLayout()
        sources_label = QLabel("数据源:")
        sources_row.addWidget(sources_label)
        self._source_cbs = {}
        source_options = [
            ("OpenAlex", "openalex", True),
            ("arXiv", "arxiv", True),
            ("Semantic Scholar", "semantic_scholar", True),
            ("CrossRef", "crossref", False),
            ("PubMed", "pubmed", False),
            ("Google Scholar", "google_scholar", False),
            ("Scopus", "scopus", False),
        ]
        for display_name, engine_key, default in source_options:
            cb = QCheckBox(display_name)
            cb.setChecked(default)
            cb.setStyleSheet(f"color: {t.get('text')};")
            cb.setProperty("engine_key", engine_key)
            self._source_cbs[engine_key] = cb
            sources_row.addWidget(cb)
        sources_row.addStretch()

        max_label = QLabel("最大结果:")
        sources_row.addWidget(max_label)
        self._kw_max = QSpinBox()
        self._kw_max.setRange(10, 200)
        self._kw_max.setValue(50)
        self._kw_max.setStyleSheet(INPUT_QSS())
        sources_row.addWidget(self._kw_max)

        search_btn = QPushButton("搜索")
        search_btn.setStyleSheet(BTN_PRIMARY_QSS())
        search_btn.clicked.connect(self._start_kw_search)
        sources_row.addWidget(search_btn)
        layout.addLayout(sources_row)

        self._kw_progress = QProgressBar()
        self._kw_progress.setVisible(False)
        self._kw_progress.setStyleSheet(f"""
            QProgressBar {{ background-color: {t.get('border')}; border-radius: 4px; height: 6px; }}
            QProgressBar::chunk {{ background-color: {t.get('accent')}; border-radius: 4px; }}
        """)
        layout.addWidget(self._kw_progress)

        self._kw_stats = QLabel("")
        self._kw_stats.setStyleSheet(f"color: {t.get('text_d')};")
        layout.addWidget(self._kw_stats)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background-color: transparent; border: none; {SCROLLBAR_QSS()}")
        self._kw_results_container = QWidget()
        self._kw_results_layout = QVBoxLayout(self._kw_results_container)
        self._kw_results_layout.setContentsMargins(0, 0, 0, 0)
        self._kw_results_layout.setSpacing(8)
        self._kw_results_layout.addStretch()
        scroll.setWidget(self._kw_results_container)
        layout.addWidget(scroll, 1)

        self._kw_groups: list[QWidget] = []
        self._add_kw_group()

        return page

    def _add_kw_group(self):
        t = self._theme
        group = QFrame()
        group.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['lg']};
                padding: 8px;
            }}
        """)
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(12, 8, 12, 8)
        g_layout.setSpacing(6)

        header = QHBoxLayout()
        or_label = QLabel("OR 组")
        or_label.setStyleSheet(f"color: {t.get('orange')}; font-weight: bold;")
        header.addWidget(or_label)
        header.addStretch()

        del_btn = QPushButton("x")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: {t.get('text_d')}; border: none; border-radius: 10px; }}
            QPushButton:hover {{ background-color: {t.get('red')}; color: white; }}
        """)
        del_btn.clicked.connect(lambda: self._remove_kw_group(group))
        header.addWidget(del_btn)
        g_layout.addLayout(header)

        kw_row = QHBoxLayout()
        inputs = []
        for i in range(3):
            inp = QLineEdit()
            inp.setPlaceholderText(f"关键词 {i + 1}")
            inp.setStyleSheet(INPUT_QSS())
            inp.setFixedHeight(32)
            kw_row.addWidget(inp)
            inputs.append(inp)
            if i < 2:
                and_label = QLabel("AND")
                and_label.setStyleSheet(f"color: {t.get('accent')}; font-weight: bold;")
                kw_row.addWidget(and_label)

        g_layout.addLayout(kw_row)
        group._inputs = inputs

        self._kw_layout.addWidget(group)
        self._kw_groups.append(group)

    def _remove_kw_group(self, group):
        if len(self._kw_groups) <= 1:
            return
        self._kw_groups.remove(group)
        self._kw_layout.removeWidget(group)
        group.deleteLater()

    def _clear_kw_groups(self):
        for group in self._kw_groups[:]:
            if len(self._kw_groups) > 1:
                self._kw_groups.remove(group)
                self._kw_layout.removeWidget(group)
                group.deleteLater()
        if self._kw_groups:
            for inp in self._kw_groups[0]._inputs:
                inp.clear()

    def _get_kw_query(self) -> list[list[str]]:
        groups = []
        for group in self._kw_groups:
            keywords = [inp.text().strip() for inp in group._inputs if inp.text().strip()]
            if keywords:
                groups.append(keywords)
        return groups

    def _start_kw_search(self):
        query_groups = self._get_kw_query()
        if not query_groups:
            self._kw_stats.setText("请输入至少一个关键词")
            self._kw_stats.setStyleSheet(f"color: {self._theme.get('orange')};")
            return

        query_parts = [" ".join(g) for g in query_groups]
        query_str = " ".join(query_parts)
        self._current_query = query_str

        sources = [key for key, cb in self._source_cbs.items() if cb.isChecked()]
        if not sources:
            self._kw_stats.setText("请至少选择一个数据源")
            self._kw_stats.setStyleSheet(f"color: {self._theme.get('orange')};")
            return

        max_results = self._kw_max.value()

        if self._search_engine is None:
            try:
                from app.search.engine import UnifiedSearchEngine
                self._search_engine = UnifiedSearchEngine()
            except Exception as e:
                self._kw_stats.setText(f"搜索引擎初始化失败: {e}")
                self._kw_stats.setStyleSheet(f"color: {self._theme.get('red')};")
                return

        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)
            self._worker.deleteLater()

        self._kw_progress.setVisible(True)
        self._kw_progress.setRange(0, 0)
        self._kw_stats.setText(f"搜索中... {query_str[:50]}")
        self._kw_stats.setStyleSheet(f"color: {self._theme.get('text_d')};")

        self._worker = _SearchWorker(self._search_engine, query_str, sources, max_results)
        self._worker.finished.connect(self._on_search_finished)
        self._worker.error.connect(self._on_search_error)
        self._worker.start()

    def _on_search_finished(self, results: list[dict]):
        self._kw_progress.setVisible(False)
        self._results = results
        if results:
            self._kw_stats.setText(f"找到 {len(results)} 篇文献")
            self._kw_stats.setStyleSheet(f"color: {self._theme.get('green')};")
        else:
            self._kw_stats.setText("未找到相关文献，请尝试修改关键词或更换数据源")
            self._kw_stats.setStyleSheet(f"color: {self._theme.get('orange')};")

        while self._kw_results_layout.count() > 1:
            item = self._kw_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, paper in enumerate(results):
            card = PaperCard(paper, index=i + 1)
            self._kw_results_layout.insertWidget(i, card)

        self._save_history("search", query=self._current_query, result_count=len(results), data=results)

    def _on_search_error(self, error: str):
        self._kw_progress.setVisible(False)
        self._kw_stats.setText(f"搜索失败: {error}")
        self._kw_stats.setStyleSheet(f"color: {self._theme.get('red')};")
        QMessageBox.warning(self, "搜索失败", f"搜索过程中发生错误:\n\n{error}")

    # ── Tab 2: 标题检索 ──────────────────────────────────────

    def _build_title_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        label = QLabel("输入文献标题（每行一个，支持模糊匹配）:")
        label.setFont(QFont("Inter", 10))
        layout.addWidget(label)

        self._title_input = QTextEdit()
        self._title_input.setStyleSheet(INPUT_QSS())
        self._title_input.setPlaceholderText("在此粘贴标题列表...")
        layout.addWidget(self._title_input, 1)

        search_btn = QPushButton("批量检索")
        search_btn.setStyleSheet(BTN_PRIMARY_QSS())
        search_btn.clicked.connect(self._title_search)
        layout.addWidget(search_btn)

        return page

    def _title_search(self):
        text = self._title_input.toPlainText().strip()
        if not text:
            return
        titles = [t.strip() for t in text.split("\n") if t.strip()]
        QMessageBox.information(self, "标题检索", f"已接收 {len(titles)} 个标题，批量检索功能开发中。")

    # ── Tab 3: AI 综述（Markdown 渲染） ──────────────────────

    def _build_review_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        info = QLabel("从关键词检索结果中选择文献，生成 AI 综述。")
        info.setStyleSheet(f"color: {t.get('text_d')};")
        layout.addWidget(info)

        # 使用 QTextBrowser 支持 Markdown 渲染
        self._review_output = QTextBrowser()
        self._review_output.setOpenExternalLinks(True)
        self._review_output.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {t.get('input')};
                color: {t.get('text')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['lg']};
                padding: 16px;
                font-family: 'Inter', 'Microsoft YaHei', sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }}
        """)
        self._review_output.setPlaceholderText("综述内容将在此显示...")
        layout.addWidget(self._review_output, 1)

        btn_row = QHBoxLayout()
        gen_btn = QPushButton("生成综述")
        gen_btn.setStyleSheet(BTN_PRIMARY_QSS())
        gen_btn.clicked.connect(self._generate_review)
        btn_row.addWidget(gen_btn)

        # 进度指示
        self._review_status = QLabel("")
        self._review_status.setStyleSheet(f"color: {t.get('text_d')};")
        btn_row.addWidget(self._review_status)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return page

    def _generate_review(self):
        """生成 AI 综述（流式 Markdown 渲染）"""
        if not self._results:
            self._review_output.setMarkdown("**提示**: 请先在关键词检索 Tab 中搜索文献。")
            return

        from app.ai.router import AIRouter
        ai = AIRouter()
        model = ai.get_model("review")
        if not model:
            self._review_output.setMarkdown("**错误**: 未配置 AI 模型，请在设置中添加。")
            return

        papers_with_abs = [p for p in self._results if p.get("abstract")]
        if not papers_with_abs:
            self._review_output.setMarkdown("**提示**: 没有包含摘要的文献，无法生成综述。")
            return

        paper_list = "\n\n".join(
            f"[{i+1}] {p['title']}\nAuthors: {', '.join(p.get('authors', []))}\n"
            f"Year: {p.get('year', '')}\nJournal: {p.get('journal', '')}\n"
            f"Abstract: {p.get('abstract', '')[:300]}"
            for i, p in enumerate(papers_with_abs[:20])
        )

        system_prompt = "你是一位学术文献综述专家。请根据以下文献摘要撰写结构化的学术文献综述。\n\n要求：\n1. 综述应包含：引言（背景与意义）、研究现状分析、主要发现与方法分类、研究趋势与不足、未来展望\n2. 引用文献时使用 [编号] 格式\n3. 语言学术规范，逻辑清晰\n4. 综述长度约 800-1500 字\n5. 使用中文撰写"
        user_prompt = f"以下是与关键词相关的 {len(papers_with_abs)} 篇文献：\n\n{paper_list}\n\n请基于以上文献撰写综述。"

        self._review_output.setMarkdown("*正在生成综述...*")
        self._review_status.setText("生成中...")

        # 停止之前的 worker
        if self._review_worker and self._review_worker.isRunning():
            self._review_worker.terminate()
            self._review_worker.wait(1000)

        self._review_buffer = ""
        self._review_worker = _ReviewWorker(ai, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        self._review_worker.chunk.connect(self._on_review_chunk)
        self._review_worker.finished.connect(self._on_review_finished)
        self._review_worker.error.connect(self._on_review_error)
        self._review_worker.start()

    def _on_review_chunk(self, text: str):
        self._review_buffer += text
        self._review_output.setMarkdown(self._review_buffer)

    def _on_review_finished(self, full_text: str):
        self._review_status.setText("综述生成完成")
        self._review_output.setMarkdown(full_text)
        self._save_history("review", query=self._current_query, result_count=len([p for p in self._results if p.get("abstract")]))

    def _on_review_error(self, error: str):
        self._review_status.setText(f"生成失败: {error}")
        self._review_output.setMarkdown(f"**错误**: {error}")

    # ── Tab 4: 选题讨论（JSON 渲染） ─────────────────────────

    def _build_topic_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        label = QLabel("描述你的研究方向或兴趣，AI 将为你生成选题建议。")
        label.setStyleSheet(f"color: {t.get('text_d')};")
        layout.addWidget(label)

        self._topic_input = QTextEdit()
        self._topic_input.setStyleSheet(INPUT_QSS())
        self._topic_input.setPlaceholderText("例如：我对基于物理信息神经网络的飞行器气动参数辨识感兴趣...")
        self._topic_input.setMaximumHeight(120)
        layout.addWidget(self._topic_input)

        discuss_btn = QPushButton("开始讨论")
        discuss_btn.setStyleSheet(BTN_PRIMARY_QSS())
        discuss_btn.clicked.connect(self._start_topic_discussion)
        layout.addWidget(discuss_btn)

        # 使用 QTextBrowser 支持 Markdown/JSON 渲染
        self._topic_output = QTextBrowser()
        self._topic_output.setOpenExternalLinks(True)
        self._topic_output.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {t.get('input')};
                color: {t.get('text')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['lg']};
                padding: 16px;
                font-family: 'Inter', 'Microsoft YaHei', sans-serif;
                font-size: 13px;
            }}
        """)
        layout.addWidget(self._topic_output, 1)

        return page

    def _start_topic_discussion(self):
        """选题讨论（JSON 美化渲染）"""
        input_text = self._topic_input.toPlainText().strip()
        if not input_text:
            self._topic_output.setMarkdown("**提示**: 请输入研究方向或兴趣。")
            return

        from app.ai.router import AIRouter
        ai = AIRouter()
        model = ai.get_model("review")
        if not model:
            self._topic_output.setMarkdown("**错误**: 未配置 AI 模型，请在设置中添加。")
            return

        system_prompt = """你是一位资深学术研究导师。请根据用户描述，输出 JSON 格式的选题方案：
{
  "analysis": "深度分析总结(200-400字)",
  "topics": [{"title": "选题名称", "description": "描述", "difficulty": "难度", "innovation": "创新点"}],
  "fields": [{"name": "领域", "description": "简述", "keywords": [{"label": "标签", "terms": ["kw1","kw2"], "logic": "AND"}]}]
}
要求：3-5个选题，3-5个领域，关键词用英文。直接输出JSON。"""

        self._topic_output.setMarkdown("*正在分析...*")
        result = ai.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"研究方向：{input_text}"}
        ], purpose="review")

        content = result.get("content", "生成失败")
        # 尝试解析 JSON 并美化渲染
        try:
            # 提取 JSON（可能被包裹在 ```json ... ``` 中）
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)
            # 渲染为 Markdown 格式
            md = self._format_topic_json(data)
            self._topic_output.setMarkdown(md)
        except (json.JSONDecodeError, IndexError):
            # JSON 解析失败，直接显示原始内容
            self._topic_output.setMarkdown(content)

        self._save_history("topic", query=input_text[:80], result_count=0, data={"raw": content})

    def _format_topic_json(self, data: dict) -> str:
        """将选题 JSON 格式化为 Markdown"""
        md = "## 选题分析\n\n"

        if "analysis" in data:
            md += f"{data['analysis']}\n\n"

        if "topics" in data:
            md += "## 选题建议\n\n"
            for i, topic in enumerate(data["topics"], 1):
                md += f"### {i}. {topic.get('title', '未命名')}\n\n"
                md += f"**描述**: {topic.get('description', '')}\n\n"
                md += f"**难度**: {topic.get('difficulty', '未知')}\n\n"
                md += f"**创新点**: {topic.get('innovation', '')}\n\n"

        if "fields" in data:
            md += "## 相关研究领域\n\n"
            for field in data["fields"]:
                md += f"### {field.get('name', '')}\n\n"
                md += f"{field.get('description', '')}\n\n"
                if "keywords" in field:
                    md += "**检索关键词**:\n\n"
                    for kw_group in field["keywords"]:
                        terms = kw_group.get("terms", [])
                        logic = kw_group.get("logic", "AND")
                        label = kw_group.get("label", "")
                        md += f"- {label}: `{' ' + logic + ' '.join(terms)}`\n"
                    md += "\n"

        return md

    # ── Tab 5: 历史记录（支持重载） ──────────────────────────

    def _build_history_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 刷新按钮
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(BTN_SECONDARY_QSS())
        refresh_btn.clicked.connect(self._load_history)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._history_table = QTableWidget()
        self._history_table.setColumnCount(5)
        self._history_table.setHorizontalHeaderLabels(["时间", "类型", "查询", "结果数", "操作"])
        self._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._history_table.setStyleSheet(TABLE_QSS())
        self._history_table.doubleClicked.connect(self._on_history_double_click)
        layout.addWidget(self._history_table)

        # 详情预览区
        self._history_preview = QTextBrowser()
        self._history_preview.setOpenExternalLinks(True)
        self._history_preview.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {t.get('input')};
                color: {t.get('text')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['lg']};
                padding: 12px;
                font-size: 12px;
            }}
        """)
        self._history_preview.setMaximumHeight(200)
        self._history_preview.setPlaceholderText("双击历史记录查看详情...")
        layout.addWidget(self._history_preview)

        return page

    def _load_history(self):
        """加载搜索历史"""
        db = get_session()
        try:
            records = (
                db.query(SearchHistory)
                .order_by(SearchHistory.created_at.desc())
                .limit(100)
                .all()
            )
            self._history_table.setRowCount(len(records))
            type_map = {"search": "搜索", "review": "综述", "topic": "选题"}
            for i, r in enumerate(records):
                self._history_table.setItem(i, 0, QTableWidgetItem(r.created_at.strftime("%Y-%m-%d %H:%M")))
                self._history_table.setItem(i, 1, QTableWidgetItem(type_map.get(r.history_type, r.history_type)))
                self._history_table.setItem(i, 2, QTableWidgetItem(r.query[:50]))
                self._history_table.setItem(i, 3, QTableWidgetItem(str(r.result_count)))

                # 操作按钮
                action_btn = QPushButton("重载")
                action_btn.setStyleSheet(BTN_GHOST_QSS())
                action_btn.setFixedHeight(24)
                action_btn.clicked.connect(lambda _, rid=r.id, rtype=r.history_type: self._reload_history(rid, rtype))
                self._history_table.setCellWidget(i, 4, action_btn)

                # 存储完整数据用于预览
                self._history_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, {
                    "id": r.id, "type": r.history_type, "query": r.query,
                    "data": r.data, "review_text": r.review_text,
                })
        finally:
            db.close()

    def _on_history_double_click(self, index):
        """双击历史记录显示详情"""
        row = index.row()
        item = self._history_table.item(row, 0)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        h_type = data.get("type", "")
        if h_type == "search":
            # 显示搜索结果摘要
            try:
                papers = json.loads(data.get("data", "[]"))
                md = f"## 搜索: {data.get('query', '')}\n\n"
                md += f"共 {len(papers)} 篇结果\n\n"
                for i, p in enumerate(papers[:10], 1):
                    md += f"{i}. **{p.get('title', '')}** ({p.get('year', '')})\n"
                self._history_preview.setMarkdown(md)
            except:
                self._history_preview.setMarkdown(f"查询: {data.get('query', '')}")
        elif h_type == "review":
            self._history_preview.setMarkdown(data.get("review_text", "无综述内容"))
        elif h_type == "topic":
            try:
                raw = json.loads(data.get("data", "{}"))
                if isinstance(raw, dict) and "raw" in raw:
                    topic_data = json.loads(raw["raw"]) if isinstance(raw["raw"], str) else raw["raw"]
                    self._history_preview.setMarkdown(self._format_topic_json(topic_data))
                else:
                    self._history_preview.setMarkdown(json.dumps(raw, ensure_ascii=False, indent=2))
            except:
                self._history_preview.setMarkdown(f"查询: {data.get('query', '')}")

    def _reload_history(self, record_id: str, h_type: str):
        """重载历史记录"""
        db = get_session()
        try:
            record = db.get(SearchHistory, record_id)
            if not record:
                return

            if h_type == "search":
                # 重新执行搜索
                self._current_query = record.query
                self._tabs.setCurrentIndex(0)  # 切换到关键词检索 Tab
                # 填充关键词（简化：直接用查询字符串）
                if self._kw_groups:
                    for inp in self._kw_groups[0]._inputs:
                        inp.clear()
                    if record.query:
                        parts = record.query.split()
                        for i, part in enumerate(parts[:3]):
                            if i < len(self._kw_groups[0]._inputs):
                                self._kw_groups[0]._inputs[i].setText(part)
                self._start_kw_search()

            elif h_type == "review":
                # 显示历史综述
                self._tabs.setCurrentIndex(2)
                self._review_output.setMarkdown(record.review_text or "无综述内容")

            elif h_type == "topic":
                # 显示历史选题
                self._tabs.setCurrentIndex(3)
                try:
                    data = json.loads(record.data or "{}")
                    if isinstance(data, dict) and "raw" in data:
                        raw = data["raw"]
                        topic_data = json.loads(raw) if isinstance(raw, str) else raw
                        self._topic_output.setMarkdown(self._format_topic_json(topic_data))
                    else:
                        self._topic_output.setMarkdown(json.dumps(data, ensure_ascii=False, indent=2))
                except:
                    self._topic_output.setMarkdown(record.query or "无内容")
        finally:
            db.close()

    # ── 通用方法 ─────────────────────────────────────────────

    def _save_history(self, h_type: str, query: str, result_count: int, data=None):
        db = get_session()
        try:
            record = SearchHistory(
                query=query[:200],
                history_type=h_type,
                result_count=result_count,
                review_text="" if h_type != "review" else (data if isinstance(data, str) else ""),
                data=json.dumps(data if data is not None else [], ensure_ascii=False)[:5000],
            )
            db.add(record)
            db.commit()
        finally:
            db.close()
