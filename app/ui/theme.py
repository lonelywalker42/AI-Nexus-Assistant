"""统一主题系统 — 暖色调双主题

设计原则:
- 暖色调统一：琥珀/蜂蜜/暖棕/奶油
- 8px 网格基准间距
- 高对比度文字 (WCAG AAA)
- 微妙的阴影层次
- 一致的圆角体系 (4/8/12/16px)
"""

from PySide6.QtCore import QObject, Signal


# ── 暗色主题（暖色调 — 琥珀之夜） ──────────────────────────
DARK_THEME: dict[str, str] = {
    # 背景层次 (由深到浅) — 暖棕色调
    "bg":           "#141210",      # 最深背景（暖黑棕）
    "bg_secondary": "#1c1916",      # 次级背景
    "sidebar":      "#1e1b18",      # 侧边栏
    "sidebar_h":    "#2a2520",      # 侧边栏 hover
    "sidebar_s":    "#352e28",      # 侧边栏 selected
    "card":         "#211e1a",      # 卡片背景
    "card_h":       "#2c2822",      # 卡片 hover
    "input":        "#1c1916",      # 输入框背景

    # 强调色 — 琥珀/蜂蜜色系
    "accent":       "#e8a84c",      # 主强调色（琥珀金）
    "accent_l":     "#f0be6a",      # 强调色 hover（亮蜂蜜）
    "accent_dim":   "#c88a30",      # 强调色 pressed（深琥珀）
    "accent_bg":    "#2e2518",      # 强调色背景（暖深棕）

    # 语义色 — 暖色调整
    "green":        "#7ac48a",      # 成功/完成（暖绿）
    "green_dim":    "#5a9e6a",      # 成功暗色
    "orange":       "#e8a040",      # 警告/待办（暖橙）
    "orange_dim":   "#c88030",      # 警告暗色
    "red":          "#e07060",      # 错误/紧急（暖红）
    "red_dim":      "#c05848",      # 错误暗色
    "blue":         "#6aaeD8",      # 信息（暖蓝）
    "blue_dim":     "#4a8eb8",      # 信息暗色
    "purple":       "#b898c8",      # 次要紫（暖紫）
    "cyan":         "#70b8c0",      # 青色（暖青）
    "yellow":       "#e8c860",      # 黄色（暖黄）
    "pink":         "#d89090",      # 粉色（暖粉）

    # 文字层次 — 暖白/米色
    "text":         "#d8d0c8",      # 主文字（暖米白）
    "text_d":       "#908878",      # 暗淡文字（暖灰）
    "text_b":       "#f0e8e0",      # 亮文字（暖亮白）
    "text_w":       "#fff8f0",      # 纯白文字（暖纯白）

    # 边框 — 暖棕色
    "border":       "#302820",      # 主边框
    "border_l":     "#403830",      # 亮边框（hover）

    # 表格
    "row_h":        "#282320",      # 行 hover
    "row_s":        "#332c26",      # 行 selected
    "row_alt":      "#1a1714",      # 交替行

    # 阴影
    "shadow":       "rgba(0, 0, 0, 0.3)",
    "shadow_l":     "rgba(0, 0, 0, 0.5)",

    # 状态栏
    "statusbar":    "#121010",
}

# ── 亮色主题（暖色调 — 蜂蜜奶油） ─────────────────────────
LIGHT_THEME: dict[str, str] = {
    # 背景层次 — 暖奶油色
    "bg":           "#faf6f0",      # 最浅背景（奶油白）
    "bg_secondary": "#f4efe6",      # 次级背景（暖灰白）
    "sidebar":      "#f0ebe2",      # 侧边栏
    "sidebar_h":    "#e8e0d4",      # 侧边栏 hover
    "sidebar_s":    "#ddd4c6",      # 侧边栏 selected
    "card":         "#ffffff",      # 卡片背景
    "card_h":       "#faf6f0",      # 卡片 hover
    "input":        "#ffffff",      # 输入框背景

    # 强调色 — 琥珀金
    "accent":       "#c88a28",      # 主强调色（深琥珀）
    "accent_l":     "#e0a040",      # 强调色 hover（亮琥珀）
    "accent_dim":   "#a87020",      # 强调色 pressed
    "accent_bg":    "#faf0e0",      # 强调色背景（浅蜂蜜）

    # 语义色 — 暖色调
    "green":        "#5a9e60",      # 成功/完成
    "green_dim":    "#4a8850",      # 成功暗色
    "orange":       "#d08020",      # 警告/待办
    "orange_dim":   "#b86818",      # 警告暗色
    "red":          "#c85040",      # 错误/紧急
    "red_dim":      "#a84030",      # 错误暗色
    "blue":         "#4888b0",      # 信息
    "blue_dim":     "#3870a0",      # 信息暗色
    "purple":       "#8870a0",      # 次要紫
    "cyan":         "#5098a0",      # 青色
    "yellow":       "#c09820",      # 黄色
    "pink":         "#b07070",      # 粉色

    # 文字层次 — 暖深色
    "text":         "#3a3228",      # 主文字（暖深棕）
    "text_d":       "#807060",      # 暗淡文字（暖灰棕）
    "text_b":       "#201810",      # 标题文字（深暖黑）
    "text_w":       "#fff8f0",      # 纯白文字

    # 边框 — 暖灰
    "border":       "#e0d8cc",      # 主边框
    "border_l":     "#d0c8b8",      # 亮边框

    # 表格
    "row_h":        "#f0ebe2",      # 行 hover
    "row_s":        "#e8e0d4",      # 行 selected
    "row_alt":      "#faf6f0",      # 交替行

    # 阴影
    "shadow":       "rgba(80, 60, 30, 0.08)",
    "shadow_l":     "rgba(80, 60, 30, 0.15)",

    # 状态栏
    "statusbar":    "#eee8de",
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
#  QSS 模板 — 暖色调组件样式
# ══════════════════════════════════════════════════════════════

def BTN_PRIMARY_QSS() -> str:
    """主按钮 — 琥珀金实心"""
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
    """次级按钮 — 暖色边框"""
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
    """危险按钮 — 暖红边框"""
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
    """幽灵按钮"""
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
