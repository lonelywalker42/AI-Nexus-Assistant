"""文献管理页面 — 5 个 Tab：关键词检索 / 标题检索 / AI综述 / 选题讨论 / 历史记录"""

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QTabWidget, QScrollArea, QFrame,
    QCheckBox, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from app.ui.theme import (
    get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, INPUT_QSS,
    COMBO_QSS, TABLE_QSS, TAB_QSS,
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


class LiteraturePage(QWidget):
    """文献管理页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._results: list[dict] = []
        self._search_engine = None
        self._worker = None
        self._current_query: str = ""
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Tab 容器
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_QSS())

        self._tabs.addTab(self._build_keyword_tab(), "🔍 关键词检索")
        self._tabs.addTab(self._build_title_tab(), "📝 标题检索")
        self._tabs.addTab(self._build_review_tab(), "📊 AI 综述")
        self._tabs.addTab(self._build_topic_tab(), "💡 选题讨论")
        self._tabs.addTab(self._build_history_tab(), "📋 历史记录")

        layout.addWidget(self._tabs)

    def refresh(self):
        self._load_history()

    # ── Tab 1: 关键词检索 ────────────────────────────────────

    def _build_keyword_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 关键词组构建器
        kw_label = QLabel("关键词组（组内 AND，组间 OR）:")
        kw_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        layout.addWidget(kw_label)

        self._kw_container = QWidget()
        self._kw_layout = QVBoxLayout(self._kw_container)
        self._kw_layout.setContentsMargins(0, 0, 0, 0)
        self._kw_layout.setSpacing(8)
        layout.addWidget(self._kw_container)

        # 添加组按钮
        kw_btn_row = QHBoxLayout()
        add_group_btn = QPushButton("➕ 添加 OR 组")
        add_group_btn.setStyleSheet(BTN_SECONDARY_QSS())
        add_group_btn.clicked.connect(self._add_kw_group)
        kw_btn_row.addWidget(add_group_btn)

        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setStyleSheet(BTN_SECONDARY_QSS())
        clear_btn.clicked.connect(self._clear_kw_groups)
        kw_btn_row.addWidget(clear_btn)
        kw_btn_row.addStretch()
        layout.addLayout(kw_btn_row)

        # 数据源选择
        sources_row = QHBoxLayout()
        sources_label = QLabel("数据源:")
        sources_row.addWidget(sources_label)
        self._source_cbs = {}
        for name, default in [("OpenAlex", True), ("arXiv", True), ("Semantic Scholar", True),
                               ("CrossRef", False), ("PubMed", False), ("Google Scholar", False), ("Scopus", False)]:
            cb = QCheckBox(name)
            cb.setChecked(default)
            cb.setStyleSheet(f"color: {t.get('text')};")
            self._source_cbs[name] = cb
            sources_row.addWidget(cb)
        sources_row.addStretch()

        max_label = QLabel("最大结果:")
        sources_row.addWidget(max_label)
        self._kw_max = QSpinBox()
        self._kw_max.setRange(10, 200)
        self._kw_max.setValue(50)
        self._kw_max.setStyleSheet(f"""
            QSpinBox {{
                background-color: {t.get('input')};
                color: {t.get('text')};
                border: 1px solid {t.get('border')};
                border-radius: 4px;
                padding: 2px 6px;
            }}
        """)
        sources_row.addWidget(self._kw_max)

        search_btn = QPushButton("🔍 搜索")
        search_btn.setStyleSheet(BTN_PRIMARY_QSS())
        search_btn.clicked.connect(self._start_kw_search)
        sources_row.addWidget(search_btn)
        layout.addLayout(sources_row)

        # 进度条
        self._kw_progress = QProgressBar()
        self._kw_progress.setVisible(False)
        self._kw_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {t.get('border')};
                border-radius: 4px;
                height: 6px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {t.get('accent')};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self._kw_progress)

        # 结果统计
        self._kw_stats = QLabel("")
        self._kw_stats.setStyleSheet(f"color: {t.get('text_d')};")
        layout.addWidget(self._kw_stats)

        # 结果列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        self._kw_results_container = QWidget()
        self._kw_results_layout = QVBoxLayout(self._kw_results_container)
        self._kw_results_layout.setContentsMargins(0, 0, 0, 0)
        self._kw_results_layout.setSpacing(8)
        self._kw_results_layout.addStretch()
        scroll.setWidget(self._kw_results_container)
        layout.addWidget(scroll, 1)

        # 初始化一个关键词组
        self._kw_groups: list[QWidget] = []
        self._add_kw_group()

        return page

    def _add_kw_group(self):
        """添加一个关键词 OR 组"""
        t = self._theme
        group = QFrame()
        group.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(8, 8, 8, 8)
        g_layout.setSpacing(4)

        header = QHBoxLayout()
        or_label = QLabel("OR 组")
        or_label.setStyleSheet(f"color: {t.get('orange')}; font-weight: bold;")
        header.addWidget(or_label)
        header.addStretch()

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.get('text_d')};
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {t.get('red')};
                color: white;
            }}
        """)
        del_btn.clicked.connect(lambda: self._remove_kw_group(group))
        header.addWidget(del_btn)
        g_layout.addLayout(header)

        # 关键词输入行
        kw_row = QHBoxLayout()
        inputs = []
        for i in range(3):
            inp = QLineEdit()
            inp.setPlaceholderText(f"关键词 {i + 1}")
            inp.setStyleSheet(INPUT_QSS())
            inp.setFixedHeight(30)
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
        """清空所有关键词组"""
        # 删除所有组（除了最后一个）
        for group in self._kw_groups[:]:
            if len(self._kw_groups) > 1:
                self._kw_groups.remove(group)
                self._kw_layout.removeWidget(group)
                group.deleteLater()
        # 清空最后一个组的输入
        if self._kw_groups:
            for inp in self._kw_groups[0]._inputs:
                inp.clear()

    def _get_kw_query(self) -> list[list[str]]:
        """获取关键词组查询"""
        groups = []
        for group in self._kw_groups:
            keywords = []
            for inp in group._inputs:
                kw = inp.text().strip()
                if kw:
                    keywords.append(kw)
            if keywords:
                groups.append(keywords)
        return groups

    def _start_kw_search(self):
        """执行关键词搜索"""
        query_groups = self._get_kw_query()
        if not query_groups:
            self._kw_stats.setText("请输入至少一个关键词")
            self._kw_stats.setStyleSheet(f"color: {self._theme.get('orange')};")
            return

        # 构建查询字符串
        query_parts = [" AND ".join(g) for g in query_groups]
        query_str = " OR ".join(query_parts)
        self._current_query = query_str

        # 获取选中的数据源
        sources = [name for name, cb in self._source_cbs.items() if cb.isChecked()]
        if not sources:
            self._kw_stats.setText("请至少选择一个数据源")
            self._kw_stats.setStyleSheet(f"color: {self._theme.get('orange')};")
            return

        max_results = self._kw_max.value()

        # 懒加载搜索引擎
        if self._search_engine is None:
            try:
                from app.search.engine import UnifiedSearchEngine
                self._search_engine = UnifiedSearchEngine()
            except Exception as e:
                self._kw_stats.setText(f"搜索引擎初始化失败: {e}")
                self._kw_stats.setStyleSheet(f"color: {self._theme.get('red')};")
                return

        # 停止之前的搜索 worker
        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)
            self._worker.deleteLater()

        self._kw_progress.setVisible(True)
        self._kw_progress.setRange(0, 0)
        self._kw_stats.setText(f"搜索中... 查询: {query_str[:50]}")
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

        # 清空结果列表
        while self._kw_results_layout.count() > 1:
            item = self._kw_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 渲染结果卡片
        for i, paper in enumerate(results):
            card = PaperCard(paper, index=i + 1)
            self._kw_results_layout.insertWidget(i, card)

        # 保存搜索历史
        self._save_history("search", query=self._current_query, result_count=len(results), data=results)

    def _on_search_error(self, error: str):
        self._kw_progress.setVisible(False)
        self._kw_stats.setText(f"搜索失败: {error}")
        self._kw_stats.setStyleSheet(f"color: {self._theme.get('red')};")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "搜索失败", f"搜索过程中发生错误:\n\n{error}\n\n请检查网络连接或稍后重试。")

    # ── Tab 2: 标题检索 ──────────────────────────────────────

    def _build_title_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        label = QLabel("输入文献标题（每行一个，支持模糊匹配）:")
        label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(label)

        self._title_input = QTextEdit()
        self._title_input.setStyleSheet(INPUT_QSS())
        self._title_input.setPlaceholderText("在此粘贴标题列表...")
        layout.addWidget(self._title_input, 1)

        search_btn = QPushButton("🔍 批量检索")
        search_btn.setStyleSheet(BTN_PRIMARY_QSS())
        search_btn.clicked.connect(self._title_search)
        layout.addWidget(search_btn)

        return page

    def _title_search(self):
        text = self._title_input.toPlainText().strip()
        if not text:
            return
        titles = [t.strip() for t in text.split("\n") if t.strip()]
        # TODO: 实现标题批量搜索
        pass

    # ── Tab 3: AI 综述 ──────────────────────────────────────

    def _build_review_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QLabel("从关键词检索结果中选择文献，生成 AI 综述。")
        info.setStyleSheet(f"color: {t.get('text_d')};")
        layout.addWidget(info)

        self._review_output = QTextEdit()
        self._review_output.setReadOnly(True)
        self._review_output.setStyleSheet(INPUT_QSS())
        layout.addWidget(self._review_output, 1)

        btn_row = QHBoxLayout()
        gen_btn = QPushButton("📊 生成综述")
        gen_btn.setStyleSheet(BTN_PRIMARY_QSS())
        gen_btn.clicked.connect(self._generate_review)
        btn_row.addWidget(gen_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return page

    # ── Tab 4: 选题讨论 ─────────────────────────────────────

    def _build_topic_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        label = QLabel("描述你的研究方向或兴趣，AI 将为你生成选题建议。")
        label.setStyleSheet(f"color: {t.get('text_d')};")
        layout.addWidget(label)

        self._topic_input = QTextEdit()
        self._topic_input.setStyleSheet(INPUT_QSS())
        self._topic_input.setPlaceholderText("例如：我对基于物理信息神经网络的飞行器气动参数辨识感兴趣...")
        self._topic_input.setMaximumHeight(120)
        layout.addWidget(self._topic_input)

        discuss_btn = QPushButton("💡 开始讨论")
        discuss_btn.setStyleSheet(BTN_PRIMARY_QSS())
        discuss_btn.clicked.connect(self._start_topic_discussion)
        layout.addWidget(discuss_btn)

        self._topic_output = QTextEdit()
        self._topic_output.setReadOnly(True)
        self._topic_output.setStyleSheet(INPUT_QSS())
        layout.addWidget(self._topic_output, 1)

        return page

    # ── Tab 3/4: AI 综述 + 选题讨论 ─────────────────────────

    def _generate_review(self):
        """生成 AI 综述"""
        if not self._results:
            self._review_output.setText("请先在关键词检索 Tab 中搜索文献。")
            return

        from app.ai.router import AIRouter
        ai = AIRouter()
        model = ai.get_model("review")
        if not model:
            self._review_output.setText("未配置 AI 模型，请在设置中添加。")
            return

        # 构建文献列表
        papers_with_abs = [p for p in self._results if p.get("abstract")]
        if not papers_with_abs:
            self._review_output.setText("没有包含摘要的文献，无法生成综述。")
            return

        paper_list = "\n\n".join(
            f"[{i+1}] {p['title']}\nAuthors: {', '.join(p.get('authors', []))}\n"
            f"Year: {p.get('year', '')}\nJournal: {p.get('journal', '')}\n"
            f"Abstract: {p.get('abstract', '')[:300]}"
            for i, p in enumerate(papers_with_abs[:20])
        )

        system_prompt = "你是一位学术文献综述专家。请根据以下文献摘要撰写结构化综述。包含：引言、研究现状、方法分类、趋势、展望。引用时使用[编号]格式。用中文撰写，约800-1500字。"
        user_prompt = f"以下是 {len(papers_with_abs)} 篇文献：\n\n{paper_list}\n\n请撰写综述。"

        self._review_output.setText("正在生成综述...")
        result = ai.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ], purpose="review")
        self._review_output.setText(result.get("content", "生成失败"))

        # 保存历史
        self._save_history("review", query=self._current_query, result_count=len(papers_with_abs))

    def _start_topic_discussion(self):
        """选题讨论"""
        input_text = self._topic_input.toPlainText().strip()
        if not input_text:
            self._topic_output.setText("请输入研究方向或兴趣。")
            return

        from app.ai.router import AIRouter
        ai = AIRouter()
        model = ai.get_model("review")
        if not model:
            self._topic_output.setText("未配置 AI 模型，请在设置中添加。")
            return

        system_prompt = """你是一位资深学术研究导师。请根据用户描述，输出 JSON 格式的选题方案：
{
  "analysis": "深度分析总结(200-400字)",
  "topics": [{"title": "选题名称", "description": "描述", "difficulty": "难度", "innovation": "创新点"}],
  "fields": [{"name": "领域", "description": "简述", "keywords": [{"label": "标签", "terms": ["kw1","kw2"], "logic": "AND"}]}]
}
要求：3-5个选题，3-5个领域，关键词用英文。直接输出JSON。"""

        self._topic_output.setText("正在分析...")
        result = ai.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"研究方向：{input_text}"}
        ], purpose="review")
        self._topic_output.setText(result.get("content", "生成失败"))

        self._save_history("topic", query=input_text[:80], result_count=0)

    # ── Tab 5: 历史记录 ─────────────────────────────────────

    def _build_history_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        self._history_table = QTableWidget()
        self._history_table.setColumnCount(5)
        self._history_table.setHorizontalHeaderLabels(["时间", "类型", "查询", "结果数", "操作"])
        self._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._history_table.setStyleSheet(TABLE_QSS())
        layout.addWidget(self._history_table)

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
            for i, r in enumerate(records):
                self._history_table.setItem(i, 0, QTableWidgetItem(r.created_at.strftime("%Y-%m-%d %H:%M")))
                type_map = {"search": "🔍 搜索", "review": "📊 综述", "topic": "💡 选题"}
                self._history_table.setItem(i, 1, QTableWidgetItem(type_map.get(r.history_type, r.history_type)))
                self._history_table.setItem(i, 2, QTableWidgetItem(r.query[:50]))
                self._history_table.setItem(i, 3, QTableWidgetItem(str(r.result_count)))
                self._history_table.setItem(i, 4, QTableWidgetItem(""))
        finally:
            db.close()

    def _save_history(self, h_type: str, query: str, result_count: int, data=None):
        """保存搜索历史"""
        db = get_session()
        try:
            record = SearchHistory(
                query=query[:200],
                history_type=h_type,
                result_count=result_count,
                data=json.dumps(data or [], ensure_ascii=False)[:5000],
            )
            db.add(record)
            db.commit()
        finally:
            db.close()
