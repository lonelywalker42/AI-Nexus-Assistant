"""文献卡片组件 — 精致设计，来源标签 + 操作按钮"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from app.ui.theme import get_theme, BTN_SECONDARY_QSS, RADIUS


class PaperCard(QFrame):
    """文献卡片"""

    detail_clicked = Signal(str)
    cite_clicked = Signal(str)
    summary_clicked = Signal(str)

    def __init__(self, paper_data: dict, index: int = 0, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._data = paper_data
        self._index = index
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['lg']};
            }}
            QFrame:hover {{
                border-color: {t.get('accent')};
                background-color: {t.get('card_h')};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # 标题行
        title_row = QHBoxLayout()
        idx_label = QLabel(f"[{self._index}]")
        idx_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        idx_label.setStyleSheet(f"color: {t.get('accent')};")
        idx_label.setFixedWidth(30)
        title_row.addWidget(idx_label)

        title = self._data.get("title", "未知标题")
        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {t.get('text_b')};")
        title_row.addWidget(title_label, 1)

        # 来源标签
        source = self._data.get("source", "")
        if source:
            src_label = QLabel(source)
            src_label.setStyleSheet(f"""
                background-color: {t.get('accent_bg')};
                color: {t.get('accent_l')};
                border-radius: {RADIUS['sm']};
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            """)
            title_row.addWidget(src_label)

        layout.addLayout(title_row)

        # 作者 + 年份 + 期刊
        authors = self._data.get("authors", [])
        year = self._data.get("year", "")
        journal = self._data.get("journal", "")
        meta_parts = []
        if authors:
            meta_parts.append(", ".join(authors[:3]) + ("..." if len(authors) > 3 else ""))
        if year:
            meta_parts.append(str(year))
        if journal:
            meta_parts.append(journal)
        meta_text = " | ".join(meta_parts)

        if meta_text:
            meta_label = QLabel(meta_text)
            meta_label.setFont(QFont("Microsoft YaHei", 9))
            meta_label.setStyleSheet(f"color: {t.get('text_d')};")
            layout.addWidget(meta_label)

        # 摘要预览
        abstract = self._data.get("abstract", "")
        if abstract:
            preview = abstract[:200] + ("..." if len(abstract) > 200 else "")
            abs_label = QLabel(preview)
            abs_label.setWordWrap(True)
            abs_label.setFont(QFont("Microsoft YaHei", 9))
            abs_label.setStyleSheet(f"color: {t.get('text_d')}; line-height: 1.4;")
            layout.addWidget(abs_label)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        for text, signal in [("详情", "detail_clicked"), ("引用", "cite_clicked"), ("AI总结", "summary_clicked")]:
            btn = QPushButton(text)
            btn.setStyleSheet(BTN_SECONDARY_QSS())
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            getattr(btn, "clicked").connect(lambda _, s=signal: getattr(self, s).emit(self._data.get("id", "")))
            btn_row.addWidget(btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def get_data(self) -> dict:
        return self._data
