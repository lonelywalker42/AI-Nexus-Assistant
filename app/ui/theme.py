"""统一主题系统 — 暗色/亮色双主题，基于 Catppuccin 色板"""

from PySide6.QtCore import QObject, Signal


# ── 暗色主题（Catppuccin Mocha） ──────────────────────────────
DARK_THEME: dict[str, str] = {
    "bg":         "#0f1117",
    "sidebar":    "#161822",
    "sidebar_h":  "#1e2030",
    "sidebar_s":  "#252840",
    "accent":     "#7c6aef",
    "accent_l":   "#9d8af0",
    "text":       "#c6cee3",
    "text_d":     "#6b7394",
    "text_b":     "#eef1f8",
    "card":       "#1a1d2e",
    "card_h":     "#222640",
    "border":     "#2a2e45",
    "input":      "#1e2136",
    "green":      "#40c790",
    "orange":     "#f0a050",
    "red":        "#ef6b6b",
    "blue":       "#6ba3ef",
    "purple":     "#b07aed",
    "row_h":      "#1e2136",
    "row_s":      "#252840",
}

# ── 亮色主题 ──────────────────────────────────────────────────
LIGHT_THEME: dict[str, str] = {
    "bg":         "#eff1f5",
    "sidebar":    "#e6e9ef",
    "sidebar_h":  "#dce0e8",
    "sidebar_s":  "#ccd0da",
    "accent":     "#7c6aef",
    "accent_l":   "#9d8af0",
    "text":       "#4c4f69",
    "text_d":     "#8c8fa1",
    "text_b":     "#1e2030",
    "card":       "#ffffff",
    "card_h":     "#f5f5f7",
    "border":     "#dce0e8",
    "input":      "#ffffff",
    "green":      "#40a02b",
    "orange":     "#df8e1d",
    "red":        "#d20f39",
    "blue":       "#1e66f5",
    "purple":     "#8839ef",
    "row_h":      "#f5f5f7",
    "row_s":      "#dce0e8",
}


class ThemeManager(QObject):
    """主题管理器 — 全局单例"""
    theme_changed = Signal(str)  # "dark" / "light"

    def __init__(self):
        super().__init__()
        self._mode: str = "dark"
        self._colors: dict[str, str] = DARK_THEME.copy()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def colors(self) -> dict[str, str]:
        return self._colors

    def get(self, key: str) -> str:
        """获取当前主题的颜色值"""
        return self._colors.get(key, "#ff00ff")  # 缺失 key 返回品红便于调试

    def set_theme(self, mode: str) -> None:
        """切换主题"""
        if mode == self._mode:
            return
        self._mode = mode
        self._colors = (DARK_THEME if mode == "dark" else LIGHT_THEME).copy()
        self.theme_changed.emit(mode)

    def toggle(self) -> str:
        """切换主题并返回新模式"""
        new_mode = "light" if self._mode == "dark" else "dark"
        self.set_theme(new_mode)
        return new_mode


# ── 全局单例 ──────────────────────────────────────────────────
_theme_manager: ThemeManager | None = None


def get_theme() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


# ── QSS 模板常量 ──────────────────────────────────────────────
def BTN_PRIMARY_QSS() -> str:
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: {t.get('accent')};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {t.get('accent_l')};
        }}
        QPushButton:pressed {{
            background-color: {t.get('accent')};
        }}
        QPushButton:disabled {{
            background-color: {t.get('text_d')};
            color: {t.get('text_d')};
        }}
    """


def BTN_SECONDARY_QSS() -> str:
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: 6px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {t.get('card_h')};
            border-color: {t.get('accent')};
        }}
    """


def BTN_DANGER_QSS() -> str:
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {t.get('red')};
            border: 1px solid {t.get('red')};
            border-radius: 6px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {t.get('red')};
            color: white;
        }}
    """


def INPUT_QSS() -> str:
    t = get_theme()
    return f"""
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {t.get('input')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: 6px;
            padding: 6px 10px;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {t.get('accent')};
        }}
    """


def COMBO_QSS() -> str:
    t = get_theme()
    return f"""
        QComboBox {{
            background-color: {t.get('input')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: 6px;
            padding: 6px 10px;
        }}
        QComboBox:hover {{
            border-color: {t.get('accent')};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {t.get('card')};
            color: {t.get('text')};
            selection-background-color: {t.get('sidebar_s')};
        }}
    """


def TABLE_QSS() -> str:
    t = get_theme()
    return f"""
        QTableWidget {{
            background-color: {t.get('bg')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: 6px;
            gridline-color: {t.get('border')};
        }}
        QTableWidget::item {{
            padding: 6px;
        }}
        QTableWidget::item:selected {{
            background-color: {t.get('row_s')};
        }}
        QHeaderView::section {{
            background-color: {t.get('sidebar')};
            color: {t.get('text_d')};
            border: none;
            border-bottom: 1px solid {t.get('border')};
            padding: 6px;
            font-weight: bold;
        }}
    """


def TAB_QSS() -> str:
    t = get_theme()
    return f"""
        QTabWidget::pane {{
            border: 1px solid {t.get('border')};
            border-radius: 6px;
            background-color: {t.get('bg')};
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {t.get('text_d')};
            padding: 8px 16px;
            border-bottom: 2px solid transparent;
        }}
        QTabBar::tab:selected {{
            color: {t.get('accent')};
            border-bottom: 2px solid {t.get('accent')};
        }}
        QTabBar::tab:hover {{
            color: {t.get('text')};
        }}
    """


def SCROLLBAR_QSS() -> str:
    t = get_theme()
    return f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t.get('border')};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t.get('text_d')};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {t.get('border')};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {t.get('text_d')};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
    """
