"""命令面板 — Ctrl+K 全局搜索 + 跨模块结果分组 + 页面快速跳转"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QFrame, QHBoxLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from app.ui.theme import get_theme
from app.db import get_session
from app.models.task import Task
from app.models.paper import Paper
from app.models.experiment import Experiment
from app.models.knowledge import KnowledgeCard


class CommandPalette(QDialog):
    """命令面板 — Ctrl+K 唤出"""

    # Signal: (page_index, item_id)
    navigate = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self.setWindowTitle("命令面板")
        self.setFixedSize(600, 400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        self.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(0, 0, 0, 120);
            }}
        """)

        # 主容器
        container = QFrame(self)
        container.setGeometry(30, 30, 540, 340)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('accent')};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # 搜索框
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 搜索任务、文献、试验、知识卡片... 或输入页面名称跳转")
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.get('input')};
                color: {t.get('text')};
                border: 1px solid {t.get('border')};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {t.get('accent')};
            }}
        """)
        self._search.textChanged.connect(self._on_search)
        self._search.returnPressed.connect(self._on_select)
        layout.addWidget(self._search)

        # 结果列表
        self._results = QListWidget()
        self._results.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                color: {t.get('text')};
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background-color: {t.get('sidebar_h')};
            }}
            QListWidget::item:selected {{
                background-color: {t.get('sidebar_s')};
                color: {t.get('accent')};
            }}
        """)
        self._results.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._results, 1)

        # 快捷键提示
        hint = QLabel("↑↓ 导航  Enter 选择  Esc 关闭")
        hint.setStyleSheet(f"color: {t.get('text_d')}; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(hint)

        # 初始显示快捷入口
        self._show_shortcuts()

    def _show_shortcuts(self):
        """显示快捷入口"""
        shortcuts = [
            ("📋  任务与日程", 0, ""),
            ("📚  文献管理", 1, ""),
            ("🧪  试验管理", 2, ""),
            ("🧠  知识库", 3, ""),
            ("💬  AI 对话", 4, ""),
            ("⚙️  设置", 5, ""),
        ]
        self._results.clear()
        for text, page_idx, item_id in shortcuts:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, (page_idx, item_id))
            self._results.addItem(item)
        self._results.setCurrentRow(0)

    def _on_search(self, text: str):
        """搜索"""
        if not text.strip():
            self._show_shortcuts()
            return

        self._results.clear()
        query = text.strip().lower()

        # 快捷页面跳转
        page_map = {
            "任务": 0, "日程": 0, "todo": 0, "task": 0,
            "文献": 1, "literature": 1, "paper": 1, "搜索": 1,
            "试验": 2, "experiment": 2, "实验": 2,
            "知识": 3, "knowledge": 3, "kb": 3,
            "对话": 4, "chat": 4, "ai": 4,
            "设置": 5, "setting": 5, "config": 5,
        }
        for keyword, page_idx in page_map.items():
            if keyword in query:
                names = ["任务与日程", "文献管理", "试验管理", "知识库", "AI 对话", "设置"]
                item = QListWidgetItem(f"📄 跳转到: {names[page_idx]}")
                item.setData(Qt.ItemDataRole.UserRole, (page_idx, ""))
                self._results.addItem(item)

        # 搜索任务
        db = get_session()
        try:
            tasks = db.query(Task).filter(Task.content.ilike(f"%{text}%")).limit(5).all()
            for task in tasks:
                status = "✅" if task.completed else "⬜"
                item = QListWidgetItem(f"{status} 📋 {task.content[:50]}")
                item.setData(Qt.ItemDataRole.UserRole, (0, task.id))
                self._results.addItem(item)

            # 搜索文献
            papers = db.query(Paper).filter(Paper.title.ilike(f"%{text}%")).limit(5).all()
            for paper in papers:
                item = QListWidgetItem(f"📚 {paper.title[:60]}")
                item.setData(Qt.ItemDataRole.UserRole, (1, paper.id))
                self._results.addItem(item)

            # 搜索试验
            exps = db.query(Experiment).filter(Experiment.title.ilike(f"%{text}%")).limit(5).all()
            for exp in exps:
                item = QListWidgetItem(f"🧪 {exp.title[:50]} [{exp.status}]")
                item.setData(Qt.ItemDataRole.UserRole, (2, exp.id))
                self._results.addItem(item)

            # 搜索知识卡片
            cards = db.query(KnowledgeCard).filter(KnowledgeCard.title.ilike(f"%{text}%")).limit(5).all()
            for card in cards:
                item = QListWidgetItem(f"🧠 {card.title[:50]}")
                item.setData(Qt.ItemDataRole.UserRole, (3, card.id))
                self._results.addItem(item)

        finally:
            db.close()

        if self._results.count() == 0:
            item = QListWidgetItem("无匹配结果")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._results.addItem(item)

        self._results.setCurrentRow(0)

    def _on_select(self):
        """选中结果"""
        item = self._results.currentItem()
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            page_idx, item_id = data
            self.navigate.emit(page_idx, item_id)
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Down:
            row = self._results.currentRow()
            if row < self._results.count() - 1:
                self._results.setCurrentRow(row + 1)
        elif event.key() == Qt.Key.Key_Up:
            row = self._results.currentRow()
            if row > 0:
                self._results.setCurrentRow(row - 1)
        else:
            super().keyPressEvent(event)
