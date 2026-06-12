"""统计卡片组件 — 精致设计，hover 高亮 + 阴影层次"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.ui.theme import get_theme, RADIUS


class StatCard(QFrame):
    """统计数字卡片"""

    def __init__(self, title: str, value: str = "0", subtitle: str = "",
                 accent: str | None = None, icon: str = "", parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._accent = accent or self._theme.get('accent')
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        # 图标 + 标题
        header = QLabel(f"{icon}  {title}" if icon else title)
        header.setFont(QFont("Microsoft YaHei", 10))
        header.setStyleSheet(f"color: {self._theme.get('text_d')};")
        layout.addWidget(header)

        # 数值
        self._value_label = QLabel(value)
        self._value_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        self._value_label.setStyleSheet(f"color: {self._accent};")
        layout.addWidget(self._value_label)

        # 副标题
        if subtitle:
            sub = QLabel(subtitle)
            sub.setFont(QFont("Microsoft YaHei", 9))
            sub.setStyleSheet(f"color: {self._theme.get('text_d')};")
            layout.addWidget(sub)

        self._update_style()

    def update_value(self, value: str):
        self._value_label.setText(value)

    def _update_style(self):
        t = self._theme
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['lg']};
                border-left: 3px solid {self._accent};
            }}
            StatCard:hover {{
                background-color: {t.get('card_h')};
                border-color: {t.get('border_l')};
                border-left-color: {self._accent};
            }}
        """)
