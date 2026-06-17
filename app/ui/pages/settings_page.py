"""设置页面 — AI 模型配置 + 主题 + 搜索设置"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSpinBox, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.theme import (
    get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, BTN_DANGER_QSS,
    INPUT_QSS, COMBO_QSS, TABLE_QSS,
)
from app.db import get_session
from app.models.model_config import ModelConfig


class SettingsPage(QWidget):
    """设置页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 24, 36, 24)
        layout.setSpacing(20)

        # 标题
        title = QLabel("⚙️ 设置")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {t.get('text_b')};")
        layout.addWidget(title)

        # ── AI 模型配置 ─────────────────────────────────────
        ai_group = self._create_group("🤖 AI 模型配置")
        ai_layout = QVBoxLayout(ai_group)

        # 模型表格
        self._model_table = QTableWidget()
        self._model_table.setColumnCount(7)
        self._model_table.setHorizontalHeaderLabels(["名称", "模型", "协议", "用途", "状态", "编辑", "删除"])
        self._model_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._model_table.setStyleSheet(TABLE_QSS())
        self._model_table.setMaximumHeight(250)
        ai_layout.addWidget(self._model_table)

        # 添加模型按钮
        add_btn = QPushButton("➕ 添加模型")
        add_btn.setStyleSheet(BTN_PRIMARY_QSS())
        add_btn.clicked.connect(self._add_model)
        ai_layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(ai_group)

        # ── 主题设置 ────────────────────────────────────────
        theme_group = self._create_group("🎨 主题设置")
        theme_layout = QHBoxLayout(theme_group)

        theme_label = QLabel("主题模式:")
        theme_layout.addWidget(theme_label)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["暗色", "亮色"])
        self._theme_combo.setCurrentIndex(0 if self._theme.mode == "dark" else 1)
        self._theme_combo.setStyleSheet(COMBO_QSS())
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self._theme_combo)
        theme_layout.addStretch()

        layout.addWidget(theme_group)

        # ── 联网搜索服务 ────────────────────────────────────────
        search_svc_group = self._create_group("联网搜索服务")
        search_svc_layout = QHBoxLayout(search_svc_group)

        self._search_status_label = QLabel("状态：检测中...")
        search_svc_layout.addWidget(self._search_status_label)

        self._search_toggle_btn = QPushButton("启动服务")
        self._search_toggle_btn.setStyleSheet(BTN_PRIMARY_QSS())
        self._search_toggle_btn.clicked.connect(self._toggle_search_service)
        search_svc_layout.addWidget(self._search_toggle_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(BTN_SECONDARY_QSS())
        refresh_btn.clicked.connect(self._check_search_status)
        search_svc_layout.addWidget(refresh_btn)
        search_svc_layout.addStretch()

        layout.addWidget(search_svc_group)

        # ── 搜索设置 ────────────────────────────────────────
        search_group = self._create_group("🔍 搜索设置")
        search_layout = QVBoxLayout(search_group)

        # 数据源
        sources_row = QHBoxLayout()
        sources_label = QLabel("默认数据源:")
        sources_row.addWidget(sources_label)
        self._source_checks = {}
        for source in ["OpenAlex", "CrossRef", "Semantic Scholar", "arXiv", "PubMed", "Google Scholar", "Scopus"]:
            cb = QCheckBox(source)
            cb.setChecked(source in ["OpenAlex", "arXiv", "Semantic Scholar"])
            cb.setStyleSheet(f"color: {t.get('text')};")
            self._source_checks[source.lower().replace(" ", "_")] = cb
            sources_row.addWidget(cb)
        sources_row.addStretch()
        search_layout.addLayout(sources_row)

        # 最大结果数
        max_row = QHBoxLayout()
        max_label = QLabel("每源最大结果数:")
        max_row.addWidget(max_label)
        self._max_results = QSpinBox()
        self._max_results.setRange(10, 200)
        self._max_results.setValue(50)
        self._max_results.setStyleSheet(f"""
            QSpinBox {{
                background-color: {t.get('input')};
                color: {t.get('text')};
                border: 1px solid {t.get('border')};
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        max_row.addWidget(self._max_results)
        max_row.addStretch()
        search_layout.addLayout(max_row)

        layout.addWidget(search_group)

        # ── 数据管理 ────────────────────────────────────────
        data_group = self._create_group("数据管理")
        data_layout = QVBoxLayout(data_group)

        btn_row1 = QHBoxLayout()
        import_lit_btn = QPushButton("导入 ai-literature JSON")
        import_lit_btn.setStyleSheet(BTN_SECONDARY_QSS())
        import_lit_btn.clicked.connect(self._import_ai_literature)
        btn_row1.addWidget(import_lit_btn)

        import_ds_btn = QPushButton("导入 DeepSeek 对话 JSON")
        import_ds_btn.setStyleSheet(BTN_SECONDARY_QSS())
        import_ds_btn.clicked.connect(self._import_deepseek)
        btn_row1.addWidget(import_ds_btn)
        data_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        import_pdf_btn = QPushButton("导入 PDF 文献")
        import_pdf_btn.setStyleSheet(BTN_SECONDARY_QSS())
        import_pdf_btn.clicked.connect(self._import_pdf)
        btn_row2.addWidget(import_pdf_btn)

        backup_btn = QPushButton("手动备份")
        backup_btn.setStyleSheet(BTN_SECONDARY_QSS())
        backup_btn.clicked.connect(self._manual_backup)
        btn_row2.addWidget(backup_btn)

        import_db_btn = QPushButton("导入 .db 恢复")
        import_db_btn.setStyleSheet(BTN_SECONDARY_QSS())
        import_db_btn.clicked.connect(self._import_db_restore)
        btn_row2.addWidget(import_db_btn)
        data_layout.addLayout(btn_row2)

        # 备份列表
        self._backup_table = QTableWidget()
        self._backup_table.setColumnCount(4)
        self._backup_table.setHorizontalHeaderLabels(["类型", "大小", "时间", "操作"])
        self._backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._backup_table.setStyleSheet(TABLE_QSS())
        self._backup_table.setMaximumHeight(200)
        data_layout.addWidget(self._backup_table)

        refresh_backup_btn = QPushButton("刷新备份列表")
        refresh_backup_btn.setStyleSheet(BTN_SECONDARY_QSS())
        refresh_backup_btn.clicked.connect(self._load_backups)
        data_layout.addWidget(refresh_backup_btn, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(data_group)

        layout.addStretch()

    def refresh(self):
        self._load_models()
        self._load_backups()
        self._check_search_status()

    def _create_group(self, title: str) -> QGroupBox:
        from app.ui.theme import GROUPBOX_QSS
        group = QGroupBox(title)
        group.setStyleSheet(GROUPBOX_QSS())
        return group

    def _load_models(self):
        """加载模型列表"""
        db = get_session()
        try:
            models = db.query(ModelConfig).all()
            self._model_table.setRowCount(len(models))
            for i, m in enumerate(models):
                self._model_table.setItem(i, 0, QTableWidgetItem(m.name))
                self._model_table.setItem(i, 1, QTableWidgetItem(m.model_name))
                self._model_table.setItem(i, 2, QTableWidgetItem(m.protocol))
                self._model_table.setItem(i, 3, QTableWidgetItem(m.purpose))

                status = "启用" if m.is_active else "禁用"
                self._model_table.setItem(i, 4, QTableWidgetItem(status))

                # 编辑按钮
                edit_btn = QPushButton("编辑")
                edit_btn.setStyleSheet(BTN_SECONDARY_QSS())
                edit_btn.setFixedSize(60, 28)
                edit_btn.clicked.connect(lambda _, mid=m.id: self._edit_model(mid))
                self._model_table.setCellWidget(i, 5, edit_btn)

                # 删除按钮
                del_btn = QPushButton("删除")
                del_btn.setStyleSheet(BTN_DANGER_QSS())
                del_btn.setFixedSize(60, 28)
                del_btn.clicked.connect(lambda _, mid=m.id: self._delete_model(mid))
                self._model_table.setCellWidget(i, 6, del_btn)
        finally:
            db.close()

    def _add_model(self):
        """添加模型对话框"""
        dialog = AddModelDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            db = get_session()
            try:
                model = ModelConfig(**data)
                db.add(model)
                db.commit()
            finally:
                db.close()
            self._load_models()

    def _edit_model(self, model_id: str):
        """编辑模型配置"""
        db = get_session()
        try:
            model = db.get(ModelConfig, model_id)
            if not model:
                return
            dialog = AddModelDialog(self, model=model)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                for key, value in data.items():
                    if hasattr(model, key):
                        setattr(model, key, value)
                db.commit()
        finally:
            db.close()
        self._load_models()

    def _delete_model(self, model_id: str):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此模型配置吗？")
        if reply == QMessageBox.StandardButton.Yes:
            db = get_session()
            try:
                model = db.get(ModelConfig, model_id)
                if model:
                    db.delete(model)
                    db.commit()
            finally:
                db.close()
            self._load_models()

    def _on_theme_changed(self, index: int):
        mode = "dark" if index == 0 else "light"
        self._theme.set_theme(mode)

    def _import_ai_literature(self):
        """从 ai-literature JSON 导入文献库和搜索历史"""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择 ai-literature 导出文件", "", "JSON (*.json)")
        if not path:
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            db = get_session()
            try:
                imported = 0
                # 导入文献库 (kbPapers)
                for paper in data.get("kbPapers", data.get("papers", [])):
                    from app.models.paper import Paper
                    existing = db.query(Paper).filter(Paper.title == paper.get("title", "")).first()
                    if not existing:
                        p = Paper(
                            title=paper.get("title", ""),
                            authors=json.dumps(paper.get("authors", []), ensure_ascii=False),
                            year=paper.get("year", 0),
                            doi=paper.get("doi", ""),
                            abstract=paper.get("abstract", paper.get("summary", "")),
                            journal=paper.get("journal", ""),
                            source="ai-literature",
                            star_rating=paper.get("starRating", 0),
                            user_notes=paper.get("userNotes", ""),
                        )
                        db.add(p)
                        imported += 1

                # 导入搜索历史
                for hist in data.get("history", []):
                    from app.models.search_history import SearchHistory
                    h = SearchHistory(
                        query=hist.get("query", ""),
                        history_type=hist.get("type", "search"),
                        result_count=hist.get("results_count", hist.get("result_count", 0)),
                        data=json.dumps(hist.get("data", hist.get("results", [])), ensure_ascii=False)[:5000],
                    )
                    db.add(h)

                db.commit()
                QMessageBox.information(self, "导入成功", f"导入 {imported} 篇文献")
            finally:
                db.close()
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入失败: {e}")

    def _import_deepseek(self):
        """从 DeepSeek Manager 对话 JSON 导入"""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择 DeepSeek 对话 JSON", "", "JSON (*.json)")
        if not path:
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            db = get_session()
            try:
                imported = 0
                # DeepSeek Manager 格式: {topics: [{sessions: [{messages}]}]}
                topics = data if isinstance(data, list) else data.get("topics", [])
                for topic in topics:
                    sessions = topic.get("sessions", []) if isinstance(topic, dict) else [topic]
                    for session in sessions:
                        messages = session.get("messages", [])
                        if not messages:
                            continue
                        # 为每个 session 创建知识卡片
                        from app.models.knowledge import KnowledgeCard
                        title = session.get("title", topic.get("title", "DeepSeek 对话"))[:200]
                        summary_parts = []
                        for msg in messages:
                            if msg.get("role") == "assistant":
                                summary_parts.append(msg.get("content", "")[:200])
                        summary = "\n".join(summary_parts)[:1000]

                        card = KnowledgeCard(
                            title=title,
                            summary=summary,
                            source_type="deepseek",
                            key_points="[]",
                        )
                        db.add(card)
                        imported += 1

                db.commit()
                QMessageBox.information(self, "导入成功", f"导入 {imported} 条对话记录")
            finally:
                db.close()
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入失败: {e}")

    def _import_pdf(self):
        """导入 PDF 文献"""
        from PySide6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(self, "选择 PDF 文件", "", "PDF (*.pdf)")
        if not files:
            return
        try:
            import fitz  # PyMuPDF
            imported = 0
            for pdf_path in files:
                doc = fitz.open(pdf_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()

                # 提取标题（第一行非空文本）
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                title = lines[0][:200] if lines else pdf_path.split("/")[-1]

                # 创建文献记录
                from app.models.paper import Paper
                db = get_session()
                try:
                    p = Paper(
                        title=title,
                        abstract=text[:2000],
                        source="pdf_import",
                        paper_type="PDF",
                    )
                    db.add(p)
                    imported += 1
                    db.commit()
                finally:
                    db.close()

            QMessageBox.information(self, "导入成功", f"导入 {imported} 个 PDF 文件")
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入失败: {e}")

    def _manual_backup(self):
        """手动备份"""
        from app.services.backup_service import create_backup
        result = create_backup("manual")
        if result:
            QMessageBox.information(self, "备份成功", f"备份已保存到:\n{result}")
            self._load_backups()
        else:
            QMessageBox.warning(self, "备份失败", "无法创建备份")

    def _import_db_restore(self):
        """从 .db 文件恢复数据"""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择数据库文件", "", "SQLite 数据库 (*.db)")
        if not path:
            return
        reply = QMessageBox.question(
            self, "确认恢复",
            f"确定要从以下文件恢复数据吗？\n{path}\n\n当前数据将被覆盖（恢复前会自动备份当前数据）。\n恢复后需要重启应用。",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from app.services.backup_service import restore_backup
            result = restore_backup(path)
            if result:
                QMessageBox.information(self, "恢复成功", "数据已恢复，请重启应用以加载恢复的数据。")
                self._load_backups()
            else:
                QMessageBox.warning(self, "恢复失败", "无法恢复数据库文件")
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", f"恢复失败: {e}")

    def _load_backups(self):
        """加载备份列表"""
        from app.services.backup_service import list_backups
        backups = list_backups()
        self._backup_table.setRowCount(len(backups))
        for i, b in enumerate(backups):
            name = b.get("name", "")
            # 类型标签
            if "manual" in name:
                label = "手动备份"
            elif "monthly" in name:
                label = "每月备份"
            elif "weekly" in name:
                label = "每周备份"
            elif "before_restore" in name:
                label = "恢复前备份"
            else:
                label = "每日备份"
            self._backup_table.setItem(i, 0, QTableWidgetItem(label))

            # 大小
            size = b.get("size", 0)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / 1024 / 1024:.1f} MB"
            self._backup_table.setItem(i, 1, QTableWidgetItem(size_str))

            # 时间
            self._backup_table.setItem(i, 2, QTableWidgetItem(b.get("time", "")))

            # 恢复按钮
            restore_btn = QPushButton("恢复")
            restore_btn.setStyleSheet(BTN_PRIMARY_QSS())
            restore_btn.setFixedSize(60, 28)
            restore_btn.clicked.connect(lambda _, p=b.get("path", ""): self._restore_backup(p))
            self._backup_table.setCellWidget(i, 3, restore_btn)

    def _restore_backup(self, backup_path: str):
        """从备份恢复"""
        reply = QMessageBox.question(
            self, "确认恢复",
            "确定要恢复到此备份吗？\n当前数据将被覆盖（恢复前会自动备份当前数据）。\n恢复后需要重启应用。",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.services.backup_service import restore_backup
        result = restore_backup(backup_path)
        if result:
            QMessageBox.information(self, "恢复成功", "数据已恢复，请重启应用以加载恢复的数据。")
            self._load_backups()
        else:
            QMessageBox.warning(self, "恢复失败", "无法恢复备份文件")

    def _check_search_status(self):
        """检查搜索服务状态"""
        from app.ai.search_service import is_search_service_running
        running = is_search_service_running()
        t = self._theme
        if running:
            self._search_status_label.setText("状态：运行中")
            self._search_status_label.setStyleSheet(f"color: {t.get('accent_green', '#10b981')};")
            self._search_toggle_btn.setText("停止服务")
        else:
            self._search_status_label.setText("状态：未启动")
            self._search_status_label.setStyleSheet(f"color: #ef4444;")
            self._search_toggle_btn.setText("启动服务")

    def _toggle_search_service(self):
        """启动/停止搜索服务"""
        from app.ai.search_service import is_search_service_running, start_search_service, stop_search_service, _find_node, _find_open_websearch_dir
        if is_search_service_running():
            stop_search_service()
        else:
            node = _find_node()
            ows_dir = _find_open_websearch_dir()
            if not node:
                QMessageBox.warning(self, "启动失败",
                    "未找到 Node.js，请安装后重启应用。\n\n"
                    "下载地址: https://nodejs.org\n"
                    "安装后请确保 Node.js 在系统 PATH 中。")
            elif not ows_dir:
                QMessageBox.warning(self, "启动失败",
                    "未找到 open-webSearch 目录。\n\n"
                    "请检查应用目录下是否存在 open-webSearch 文件夹。")
            else:
                ok = start_search_service()
                if not ok:
                    QMessageBox.warning(self, "启动失败",
                        "搜索服务启动超时，请检查：\n"
                        "1. 端口 3210 是否被其他程序占用\n"
                        "2. 查看 data/search_service.log 日志")
        self._check_search_status()


class AddModelDialog(QDialog):
    """添加/编辑 AI 模型对话框"""

    def __init__(self, parent=None, model=None):
        super().__init__(parent)
        self._model = model
        self.setWindowTitle("编辑 AI 模型" if model else "添加 AI 模型")
        self.setMinimumWidth(450)
        t = get_theme()
        self.setStyleSheet(f"background-color: {t.get('bg')}; color: {t.get('text')};")

        layout = QFormLayout(self)

        self._name = QLineEdit()
        self._name.setStyleSheet(INPUT_QSS())
        if model:
            self._name.setText(model.name)
        layout.addRow("名称:", self._name)

        self._url = QLineEdit()
        self._url.setPlaceholderText("https://api.deepseek.com/v1")
        self._url.setStyleSheet(INPUT_QSS())
        if model:
            self._url.setText(model.base_url)
        layout.addRow("Base URL:", self._url)

        self._key = QLineEdit()
        self._key.setPlaceholderText("sk-...")
        self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._key.setStyleSheet(INPUT_QSS())
        if model:
            self._key.setText(model.api_key)
        layout.addRow("API Key:", self._key)

        self._model_name = QLineEdit()
        self._model_name.setPlaceholderText("deepseek-reasoner")
        self._model_name.setStyleSheet(INPUT_QSS())
        if model:
            self._model_name.setText(model.model_name)
        layout.addRow("模型名称:", self._model_name)

        self._protocol = QComboBox()
        self._protocol.addItems(["openai", "anthropic"])
        self._protocol.setStyleSheet(COMBO_QSS())
        if model:
            self._protocol.setCurrentText(model.protocol)
        layout.addRow("协议:", self._protocol)

        self._purpose = QComboBox()
        self._purpose.addItems(["all", "summary", "review", "chat"])
        self._purpose.setStyleSheet(COMBO_QSS())
        if model:
            self._purpose.setCurrentText(model.purpose)
        layout.addRow("用途:", self._purpose)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "name": self._name.text().strip(),
            "base_url": self._url.text().strip(),
            "api_key": self._key.text().strip(),
            "model_name": self._model_name.text().strip(),
            "protocol": self._protocol.currentText(),
            "purpose": self._purpose.currentText(),
            "is_active": True,
        }
