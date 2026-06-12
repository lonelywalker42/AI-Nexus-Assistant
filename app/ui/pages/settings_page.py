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
        self._model_table.setColumnCount(6)
        self._model_table.setHorizontalHeaderLabels(["名称", "模型", "协议", "用途", "状态", "操作"])
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
        data_group = self._create_group("💾 数据管理")
        data_layout = QHBoxLayout(data_group)

        import_btn = QPushButton("📥 从 ai-literature 导入")
        import_btn.setStyleSheet(BTN_SECONDARY_QSS())
        import_btn.clicked.connect(self._import_data)
        data_layout.addWidget(import_btn)

        backup_btn = QPushButton("📦 手动备份")
        backup_btn.setStyleSheet(BTN_SECONDARY_QSS())
        data_layout.addWidget(backup_btn)

        data_layout.addStretch()
        layout.addWidget(data_group)

        layout.addStretch()

    def refresh(self):
        self._load_models()

    def _create_group(self, title: str) -> QGroupBox:
        t = self._theme
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: 8px;
                margin-top: 12px;
                padding: 16px 12px 12px 12px;
                font-weight: bold;
                color: {t.get('text_b')};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }}
        """)
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

                status = "✅ 启用" if m.is_active else "❌ 禁用"
                self._model_table.setItem(i, 4, QTableWidgetItem(status))

                del_btn = QPushButton("删除")
                del_btn.setStyleSheet(BTN_DANGER_QSS())
                del_btn.setFixedSize(60, 28)
                del_btn.clicked.connect(lambda _, mid=m.id: self._delete_model(mid))
                self._model_table.setCellWidget(i, 5, del_btn)
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

    def _import_data(self):
        """从 ai-literature 导入数据"""
        QMessageBox.information(self, "导入", "请先导出 ai-literature 的 JSON 文件，然后选择文件导入。\n\n此功能将在后续版本完善。")


class AddModelDialog(QDialog):
    """添加 AI 模型对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加 AI 模型")
        self.setMinimumWidth(450)
        t = get_theme()
        self.setStyleSheet(f"background-color: {t.get('bg')}; color: {t.get('text')};")

        layout = QFormLayout(self)

        self._name = QLineEdit()
        self._name.setStyleSheet(INPUT_QSS())
        layout.addRow("名称:", self._name)

        self._url = QLineEdit()
        self._url.setPlaceholderText("https://api.deepseek.com/v1")
        self._url.setStyleSheet(INPUT_QSS())
        layout.addRow("Base URL:", self._url)

        self._key = QLineEdit()
        self._key.setPlaceholderText("sk-...")
        self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._key.setStyleSheet(INPUT_QSS())
        layout.addRow("API Key:", self._key)

        self._model = QLineEdit()
        self._model.setPlaceholderText("deepseek-reasoner")
        self._model.setStyleSheet(INPUT_QSS())
        layout.addRow("模型名称:", self._model)

        self._protocol = QComboBox()
        self._protocol.addItems(["openai", "anthropic"])
        self._protocol.setStyleSheet(COMBO_QSS())
        layout.addRow("协议:", self._protocol)

        self._purpose = QComboBox()
        self._purpose.addItems(["all", "summary", "review", "chat"])
        self._purpose.setStyleSheet(COMBO_QSS())
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
            "model_name": self._model.text().strip(),
            "protocol": self._protocol.currentText(),
            "purpose": self._purpose.currentText(),
            "is_active": True,
        }
