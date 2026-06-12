"""知识库页面 — 知识卡片列表 + 搜索 + 分类 + 标签管理"""

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QSplitter, QListWidget,
    QListWidgetItem, QFrame, QScrollArea, QDialog, QFormLayout,
    QDialogButtonBox, QSpinBox, QGridLayout, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.theme import (
    get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, BTN_DANGER_QSS,
    INPUT_QSS, COMBO_QSS, LIST_WIDGET_QSS, SCROLLBAR_QSS, RADIUS,
)
from app.db import get_session
from app.services import knowledge_service


class KnowledgePage(QWidget):
    """知识库页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._current_card_id: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 左侧：筛选 + 标签 ──────────────────────────────
        left = QWidget()
        left.setFixedWidth(240)
        left.setStyleSheet(f"background-color: {t.get('sidebar')};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        # 搜索
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 搜索知识卡片...")
        self._search.setStyleSheet(INPUT_QSS())
        self._search.textChanged.connect(self._refresh_cards)
        left_layout.addWidget(self._search)

        # 来源过滤
        self._source_filter = QComboBox()
        self._source_filter.addItems(["全部来源", "手动创建", "文献导入", "AI对话"])
        self._source_filter.setStyleSheet(COMBO_QSS())
        self._source_filter.currentIndexChanged.connect(self._refresh_cards)
        left_layout.addWidget(self._source_filter)

        # 统计
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(f"color: {t.get('text_d')};")
        left_layout.addWidget(self._stats_label)

        # 标签列表
        tags_header = QLabel("🏷️ 标签")
        tags_header.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        left_layout.addWidget(tags_header)

        self._tag_list = QListWidget()
        self._tag_list.setMaximumHeight(200)
        self._tag_list.setStyleSheet(LIST_WIDGET_QSS())
        self._tag_list.currentTextChanged.connect(self._on_tag_selected)
        left_layout.addWidget(self._tag_list, 1)

        # 新建按钮
        add_btn = QPushButton("➕ 新建卡片")
        add_btn.setStyleSheet(BTN_PRIMARY_QSS())
        add_btn.clicked.connect(self._add_card)
        left_layout.addWidget(add_btn)

        splitter.addWidget(left)

        # ── 右侧：卡片网格 + 详情 ──────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(8)

        # 卡片标题
        self._header = QLabel("📚 知识库")
        self._header.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self._header.setStyleSheet(f"color: {t.get('text_b')};")
        right_layout.addWidget(self._header)

        # 卡片滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        self._cards_container = QWidget()
        self._cards_layout = QGridLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        scroll.setWidget(self._cards_container)
        right_layout.addWidget(scroll, 1)

        # 底部详情区
        self._detail_panel = QFrame()
        self._detail_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: 8px;
            }}
        """)
        self._detail_panel.setVisible(False)
        detail_layout = QVBoxLayout(self._detail_panel)
        detail_layout.setContentsMargins(16, 12, 16, 12)

        self._detail_title = QLabel("")
        self._detail_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        detail_layout.addWidget(self._detail_title)

        self._detail_summary = QTextEdit()
        self._detail_summary.setStyleSheet(INPUT_QSS())
        self._detail_summary.setMaximumHeight(80)
        detail_layout.addWidget(self._detail_summary)

        self._detail_notes = QTextEdit()
        self._detail_notes.setStyleSheet(INPUT_QSS())
        self._detail_notes.setPlaceholderText("用户笔记...")
        self._detail_notes.setMaximumHeight(60)
        detail_layout.addWidget(self._detail_notes)

        # 星级
        star_row = QHBoxLayout()
        self._star_buttons = []
        for i in range(1, 6):
            btn = QPushButton("☆")
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    font-size: 16px;
                    color: {t.get('orange')};
                }}
            """)
            btn.clicked.connect(lambda _, s=i: self._set_star(s))
            star_row.addWidget(btn)
            self._star_buttons.append(btn)
        star_row.addStretch()

        save_btn = QPushButton("💾 保存")
        save_btn.setStyleSheet(BTN_PRIMARY_QSS())
        save_btn.clicked.connect(self._save_card_detail)
        star_row.addWidget(save_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.get('text_d')};
                border: none;
            }}
        """)
        close_btn.clicked.connect(lambda: self._detail_panel.setVisible(False))
        star_row.addWidget(close_btn)

        detail_layout.addLayout(star_row)
        right_layout.addWidget(self._detail_panel)

        splitter.addWidget(right)
        splitter.setSizes([240, 760])
        layout.addWidget(splitter)

    def refresh(self):
        self._refresh_cards()
        self._refresh_tags()
        self._refresh_stats()

    def _refresh_cards(self):
        # Clear grid
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        db = get_session()
        try:
            source_map = {0: "", 1: "manual", 2: "literature", 3: "deepseek"}
            source = source_map.get(self._source_filter.currentIndex(), "")
            search = self._search.text().strip()

            # Check if a tag is selected
            tag = ""
            current_tag = self._tag_list.currentItem()
            if current_tag:
                tag = current_tag.text().split(" ")[0]  # Remove count

            cards = knowledge_service.get_cards(db, search, source_type=source, tag=tag)

            for i, card in enumerate(cards):
                card_widget = self._create_card_widget(card)
                row, col = divmod(i, 3)
                self._cards_layout.addWidget(card_widget, row, col)
        finally:
            db.close()

    def _create_card_widget(self, card) -> QFrame:
        t = self._theme
        frame = QFrame()
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['xl']};
                padding: 8px;
            }}
            QFrame:hover {{
                border-color: {t.get('accent')};
                background-color: {t.get('card_h')};
            }}
        """)
        frame.setMinimumHeight(120)
        frame.mousePressEvent = lambda _, cid=card.id: self._show_detail(cid)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # 来源标签
        source_map = {"manual": "✏️ 手动", "literature": "📚 文献", "deepseek": "🤖 AI"}
        src = QLabel(source_map.get(card.source_type, card.source_type))
        src.setStyleSheet(f"color: {t.get('text_d')}; font-size: 10px;")
        layout.addWidget(src)

        # 标题
        title = QLabel(card.title[:60])
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        title.setWordWrap(True)
        title.setStyleSheet(f"color: {t.get('text_b')};")
        layout.addWidget(title)

        # 摘要预览
        if card.summary:
            preview = QLabel(card.summary[:100] + ("..." if len(card.summary) > 100 else ""))
            preview.setWordWrap(True)
            preview.setStyleSheet(f"color: {t.get('text_d')}; font-size: 9px;")
            layout.addWidget(preview)

        # 星级
        if card.star_rating > 0:
            stars = QLabel("★" * card.star_rating + "☆" * (5 - card.star_rating))
            stars.setStyleSheet(f"color: {t.get('orange')}; font-size: 11px;")
            layout.addWidget(stars)

        return frame

    def _refresh_tags(self):
        self._tag_list.clear()
        db = get_session()
        try:
            tags = knowledge_service.get_tags(db)
            for tag in tags:
                self._tag_list.addItem(f"{tag.name} ({tag.usage_count})")
        finally:
            db.close()

    def _refresh_stats(self):
        db = get_session()
        try:
            stats = knowledge_service.get_card_stats(db)
            self._stats_label.setText(
                f"共 {stats['total']} 张卡片 | {stats['tag_count']} 个标签"
            )
        finally:
            db.close()

    def _on_tag_selected(self, text: str):
        self._refresh_cards()

    def _show_detail(self, card_id: str):
        self._current_card_id = card_id
        db = get_session()
        try:
            card = knowledge_service.get_card(db, card_id)
            if not card:
                return
            self._detail_title.setText(card.title)
            self._detail_summary.setText(card.summary)
            self._detail_notes.setText(card.user_notes)
            self._update_star_display(card.star_rating)
        finally:
            db.close()
        self._detail_panel.setVisible(True)

    def _update_star_display(self, rating: int):
        for i, btn in enumerate(self._star_buttons):
            btn.setText("★" if i < rating else "☆")

    def _set_star(self, rating: int):
        self._update_star_display(rating)
        if self._current_card_id:
            db = get_session()
            try:
                knowledge_service.update_card(db, self._current_card_id, star_rating=rating)
            finally:
                db.close()

    def _save_card_detail(self):
        if not self._current_card_id:
            return
        db = get_session()
        try:
            knowledge_service.update_card(
                db, self._current_card_id,
                summary=self._detail_summary.toPlainText(),
                user_notes=self._detail_notes.toPlainText(),
            )
        finally:
            db.close()
        self._refresh_cards()

    def _add_card(self):
        dialog = AddCardDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            db = get_session()
            try:
                knowledge_service.create_card(db, **data)
            finally:
                db.close()
            self.refresh()


class AddCardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建知识卡片")
        self.setMinimumWidth(450)
        t = get_theme()
        self.setStyleSheet(f"background-color: {t.get('bg')}; color: {t.get('text')};")

        layout = QFormLayout(self)

        self._title = QLineEdit()
        self._title.setStyleSheet(INPUT_QSS())
        layout.addRow("标题:", self._title)

        self._summary = QTextEdit()
        self._summary.setStyleSheet(INPUT_QSS())
        self._summary.setMaximumHeight(80)
        layout.addRow("摘要:", self._summary)

        self._category = QLineEdit()
        self._category.setStyleSheet(INPUT_QSS())
        self._category.setPlaceholderText("如: 控制/飞行控制/PID")
        layout.addRow("分类路径:", self._category)

        self._tags = QLineEdit()
        self._tags.setStyleSheet(INPUT_QSS())
        self._tags.setPlaceholderText("逗号分隔，如: PINN,飞行控制,神经网络")
        layout.addRow("标签:", self._tags)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        tags = [t.strip() for t in self._tags.text().split(",") if t.strip()]
        return {
            "title": self._title.text().strip(),
            "summary": self._summary.toPlainText().strip(),
            "category_path": self._category.text().strip(),
            "tags": tags,
        }
