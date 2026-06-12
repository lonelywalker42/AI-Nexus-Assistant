"""统一主题系统 — 暗色/亮色双主题，精致 Catppuccin 色板

设计原则:
- 8px 网格基准间距
- 高对比度文字 (WCAG AAA)
- 微妙的阴影层次
- 平滑的状态过渡
- 一致的圆角体系 (4/8/12/16px)
"""

from PySide6.QtCore import QObject, Signal


# ── 暗色主题（Catppuccin Mocha 精致版） ─────────────────────
DARK_THEME: dict[str, str] = {
    # 背景层次 (由深到浅)
    "bg":           "#0b0d13",      # 最深背景
    "bg_secondary": "#111320",      # 次级背景
    "sidebar":      "#131625",      # 侧边栏
    "sidebar_h":    "#1a1e33",      # 侧边栏 hover
    "sidebar_s":    "#222744",      # 侧边栏 selected
    "card":         "#171b2e",      # 卡片背景
    "card_h":       "#1e2240",      # 卡片 hover
    "input":        "#151930",      # 输入框背景

    # 强调色
    "accent":       "#7c6aef",      # 主强调色（紫）
    "accent_l":     "#9d8af0",      # 强调色 hover
    "accent_dim":   "#5b4dc7",      # 强调色 pressed
    "accent_bg":    "#2a2450",      # 强调色背景

    # 语义色
    "green":        "#40c790",      # 成功/完成
    "green_dim":    "#2a8f65",      # 成功暗色
    "orange":       "#f0a050",      # 警告/待办
    "orange_dim":   "#b87a3a",      # 警告暗色
    "red":          "#ef6b6b",      # 错误/紧急
    "red_dim":      "#c44e4e",      # 错误暗色
    "blue":         "#6ba3ef",      # 信息
    "blue_dim":     "#4d7ec4",      # 信息暗色
    "purple":       "#b07aed",      # 次要紫
    "cyan":         "#7dc4e4",      # 青色
    "yellow":       "#f9e2af",      # 黄色
    "pink":         "#f5c2e7",      # 粉色

    # 文字层次
    "text":         "#c6cee3",      # 主文字
    "text_d":       "#6b7394",      # 暗淡文字
    "text_b":       "#eef1f8",      # 亮文字（标题）
    "text_w":       "#ffffff",      # 纯白文字（按钮上）

    # 边框
    "border":       "#2a2e45",      # 主边框
    "border_l":     "#363b58",      # 亮边框（hover）

    # 表格
    "row_h":        "#1a1e33",      # 行 hover
    "row_s":        "#222744",      # 行 selected
    "row_alt":      "#141828",      # 交替行

    # 阴影
    "shadow":       "rgba(0, 0, 0, 0.3)",
    "shadow_l":     "rgba(0, 0, 0, 0.5)",

    # 状态栏
    "statusbar":    "#0e1019",
}

# ── 亮色主题（精致版） ──────────────────────────────────────
LIGHT_THEME: dict[str, str] = {
    "bg":           "#f8f9fc",
    "bg_secondary": "#f0f2f7",
    "sidebar":      "#eef0f6",
    "sidebar_h":    "#e4e7ef",
    "sidebar_s":    "#d8dce8",
    "card":         "#ffffff",
    "card_h":       "#f5f6fa",
    "input":        "#ffffff",

    "accent":       "#6c5ce7",
    "accent_l":     "#8577ed",
    "accent_dim":   "#5a4bd6",
    "accent_bg":    "#ede9fc",

    "green":        "#2ecc71",
    "green_dim":    "#27ae60",
    "orange":       "#f39c12",
    "orange_dim":   "#d68910",
    "red":          "#e74c3c",
    "red_dim":      "#c0392b",
    "blue":         "#3498db",
    "blue_dim":     "#2980b9",
    "purple":       "#9b59b6",
    "cyan":         "#1abc9c",
    "yellow":       "#f1c40f",
    "pink":         "#e91e63",

    "text":         "#2c3e50",
    "text_d":       "#7f8c8d",
    "text_b":       "#1a1a2e",
    "text_w":       "#ffffff",

    "border":       "#dce1ea",
    "border_l":     "#c8ceda",

    "row_h":        "#f0f2f7",
    "row_s":        "#e4e7ef",
    "row_alt":      "#f8f9fc",

    "shadow":       "rgba(0, 0, 0, 0.08)",
    "shadow_l":     "rgba(0, 0, 0, 0.15)",

    "statusbar":    "#eef0f6",
}


class ThemeManager(QObject):
    """主题管理器 — 全局单例"""
    theme_changed = Signal(str)

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
        return self._colors.get(key, "#ff00ff")

    def set_theme(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self._colors = (DARK_THEME if mode == "dark" else LIGHT_THEME).copy()
        self.theme_changed.emit(mode)

    def toggle(self) -> str:
        new_mode = "light" if self._mode == "dark" else "dark"
        self.set_theme(new_mode)
        return new_mode


_theme_manager: ThemeManager | None = None


def get_theme() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


# ── 间距常量 (8px 网格) ──────────────────────────────────────
SPACING = {
    "xs": "4px",
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
    "xl": "24px",
    "2xl": "32px",
    "3xl": "48px",
}

# ── 圆角常量 ─────────────────────────────────────────────────
RADIUS = {
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "full": "9999px",
}


# ══════════════════════════════════════════════════════════════
#  QSS 模板 — 精致组件样式
# ══════════════════════════════════════════════════════════════

def BTN_PRIMARY_QSS() -> str:
    """主按钮 — 实心紫色"""
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: {t.get('accent')};
            color: {t.get('text_w')};
            border: none;
            border-radius: {RADIUS['md']};
            padding: 8px 20px;
            font-weight: bold;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {t.get('accent_l')};
        }}
        QPushButton:pressed {{
            background-color: {t.get('accent_dim')};
        }}
        QPushButton:disabled {{
            background-color: {t.get('border')};
            color: {t.get('text_d')};
        }}
    """


def BTN_SECONDARY_QSS() -> str:
    """次级按钮 — 边框样式"""
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['md']};
            padding: 8px 20px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {t.get('card_h')};
            border-color: {t.get('accent')};
            color: {t.get('accent_l')};
        }}
        QPushButton:pressed {{
            background-color: {t.get('accent_bg')};
        }}
    """


def BTN_DANGER_QSS() -> str:
    """危险按钮 — 红色边框"""
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {t.get('red')};
            border: 1px solid {t.get('red_dim')};
            border-radius: {RADIUS['md']};
            padding: 8px 20px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {t.get('red')};
            color: {t.get('text_w')};
            border-color: {t.get('red')};
        }}
        QPushButton:pressed {{
            background-color: {t.get('red_dim')};
        }}
    """


def BTN_GHOST_QSS() -> str:
    """幽灵按钮 — 无边框"""
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {t.get('text_d')};
            border: none;
            border-radius: {RADIUS['md']};
            padding: 6px 12px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {t.get('card_h')};
            color: {t.get('text')};
        }}
    """


def INPUT_QSS() -> str:
    """输入框"""
    t = get_theme()
    return f"""
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {t.get('input')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['md']};
            padding: 8px 12px;
            font-size: 13px;
            selection-background-color: {t.get('accent_bg')};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {t.get('accent')};
            background-color: {t.get('card')};
        }}
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
            border-color: {t.get('border_l')};
        }}
    """


def COMBO_QSS() -> str:
    """下拉框"""
    t = get_theme()
    return f"""
        QComboBox {{
            background-color: {t.get('input')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['md']};
            padding: 8px 12px;
            font-size: 13px;
            min-height: 20px;
        }}
        QComboBox:hover {{
            border-color: {t.get('border_l')};
        }}
        QComboBox:focus {{
            border-color: {t.get('accent')};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
            subcontrol-position: center right;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {t.get('text_d')};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {t.get('card')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['md']};
            padding: 4px;
            selection-background-color: {t.get('sidebar_s')};
            selection-color: {t.get('accent_l')};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 12px;
            border-radius: {RADIUS['sm']};
            min-height: 28px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {t.get('sidebar_h')};
        }}
    """


def TABLE_QSS() -> str:
    """表格"""
    t = get_theme()
    return f"""
        QTableWidget {{
            background-color: {t.get('bg')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['md']};
            gridline-color: {t.get('border')};
            font-size: 13px;
        }}
        QTableWidget::item {{
            padding: 8px 12px;
            border-bottom: 1px solid transparent;
        }}
        QTableWidget::item:hover {{
            background-color: {t.get('row_h')};
        }}
        QTableWidget::item:selected {{
            background-color: {t.get('row_s')};
            color: {t.get('accent_l')};
        }}
        QHeaderView::section {{
            background-color: {t.get('sidebar')};
            color: {t.get('text_d')};
            border: none;
            border-bottom: 2px solid {t.get('border')};
            padding: 10px 12px;
            font-weight: bold;
            font-size: 12px;
            text-transform: uppercase;
        }}
        QHeaderView::section:hover {{
            background-color: {t.get('sidebar_h')};
            color: {t.get('text')};
        }}
    """


def TAB_QSS() -> str:
    """Tab 页签"""
    t = get_theme()
    return f"""
        QTabWidget::pane {{
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['md']};
            background-color: {t.get('bg')};
            top: -1px;
        }}
        QTabBar {{
            background-color: transparent;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {t.get('text_d')};
            padding: 10px 20px;
            border-bottom: 2px solid transparent;
            font-size: 13px;
            font-weight: 500;
            margin-right: 4px;
        }}
        QTabBar::tab:selected {{
            color: {t.get('accent')};
            border-bottom: 2px solid {t.get('accent')};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            color: {t.get('text')};
            background-color: {t.get('card_h')};
            border-radius: {RADIUS['md']} {RADIUS['md']} 0 0;
        }}
    """


def SCROLLBAR_QSS() -> str:
    """滚动条"""
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
            min-height: 40px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t.get('text_d')};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {t.get('border')};
            border-radius: 4px;
            min-width: 40px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {t.get('text_d')};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
    """


def LIST_WIDGET_QSS() -> str:
    """列表组件"""
    t = get_theme()
    return f"""
        QListWidget {{
            background-color: transparent;
            border: none;
            outline: none;
            font-size: 13px;
        }}
        QListWidget::item {{
            padding: 10px 14px;
            border-radius: {RADIUS['md']};
            color: {t.get('text')};
            margin: 2px 4px;
        }}
        QListWidget::item:hover {{
            background-color: {t.get('sidebar_h')};
        }}
        QListWidget::item:selected {{
            background-color: {t.get('sidebar_s')};
            color: {t.get('accent_l')};
            font-weight: bold;
        }}
    """


def CARD_QSS() -> str:
    """卡片容器"""
    t = get_theme()
    return f"""
        QFrame {{
            background-color: {t.get('card')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['lg']};
        }}
        QFrame:hover {{
            border-color: {t.get('border_l')};
            background-color: {t.get('card_h')};
        }}
    """


def CARD_ACCENT_QSS(accent_color_key: str = "accent") -> str:
    """带强调色边框的卡片"""
    t = get_theme()
    color = t.get(accent_color_key)
    return f"""
        QFrame {{
            background-color: {t.get('card')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['lg']};
            border-left: 3px solid {color};
        }}
        QFrame:hover {{
            border-color: {t.get('border_l')};
            border-left-color: {color};
            background-color: {t.get('card_h')};
        }}
    """


def RADIO_QSS() -> str:
    """单选按钮"""
    t = get_theme()
    return f"""
        QRadioButton {{
            color: {t.get('text')};
            spacing: 8px;
            font-size: 13px;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 2px solid {t.get('border')};
            background-color: {t.get('input')};
        }}
        QRadioButton::indicator:hover {{
            border-color: {t.get('accent')};
        }}
        QRadioButton::indicator:checked {{
            background-color: {t.get('accent')};
            border-color: {t.get('accent')};
        }}
    """


def CHECKBOX_QSS() -> str:
    """复选框"""
    t = get_theme()
    return f"""
        QCheckBox {{
            color: {t.get('text')};
            spacing: 8px;
            font-size: 13px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 2px solid {t.get('border')};
            background-color: {t.get('input')};
        }}
        QCheckBox::indicator:hover {{
            border-color: {t.get('accent')};
        }}
        QCheckBox::indicator:checked {{
            background-color: {t.get('accent')};
            border-color: {t.get('accent')};
        }}
    """


def GROUPBOX_QSS() -> str:
    """分组框"""
    t = get_theme()
    return f"""
        QGroupBox {{
            background-color: {t.get('card')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['lg']};
            margin-top: 14px;
            padding: 20px 16px 16px 16px;
            font-weight: bold;
            font-size: 14px;
            color: {t.get('text_b')};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
            background-color: {t.get('card')};
        }}
    """


def SPLASH_QSS() -> str:
    """启动画面"""
    t = get_theme()
    return f"""
        QSplashScreen {{
            background-color: {t.get('bg')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['xl']};
        }}
    """


def TOOLTIP_QSS() -> str:
    """工具提示"""
    t = get_theme()
    return f"""
        QToolTip {{
            background-color: {t.get('card')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: {RADIUS['sm']};
            padding: 6px 10px;
            font-size: 12px;
        }}
    """
