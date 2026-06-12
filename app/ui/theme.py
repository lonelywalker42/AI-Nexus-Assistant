"""统一主题系统 — 玻璃质感 + 清新蓝绿配色

设计原则:
- 玻璃质感 (Glassmorphism): 半透明白色 + 模糊背景 + 柔和阴影
- 清新配色: 浅蓝→浅绿渐变背景，蓝/绿强调色
- 高圆角: 16-24px 大面积圆角
- 清晰字体: Inter/Segoe UI，深灰蓝文字
- 8px 网格基准间距
"""

from PySide6.QtCore import QObject, Signal


# ── 浅色主题（清新玻璃质感 — 默认主题） ─────────────────────
LIGHT_THEME: dict[str, str] = {
    # 背景层次 — 浅蓝→浅绿渐变基调
    "bg":           "#f0f7ff",      # 主背景（浅蓝白）
    "bg_secondary": "#e8f4f8",      # 次级背景（浅青白）
    "sidebar":      "#ffffff",      # 侧边栏（纯白玻璃）
    "sidebar_h":    "#f0f8ff",      # 侧边栏 hover
    "sidebar_s":    "#e0f0ff",      # 侧边栏 selected
    "card":         "#ffffff",      # 卡片背景（纯白）
    "card_h":       "#f8fbff",      # 卡片 hover
    "input":        "#ffffff",      # 输入框背景

    # 强调色 — 蓝/绿双色系
    "accent":       "#3b82f6",      # 主强调色（蓝）
    "accent_l":     "#60a5fa",      # 强调色 hover（亮蓝）
    "accent_dim":   "#2563eb",      # 强调色 pressed（深蓝）
    "accent_bg":    "#eff6ff",      # 强调色背景（浅蓝）

    # 语义色
    "green":        "#10b981",      # 成功/完成（翠绿）
    "green_dim":    "#059669",      # 成功暗色
    "orange":       "#f59e0b",      # 警告/待办（琥珀）
    "orange_dim":   "#d97706",      # 警告暗色
    "red":          "#ef4444",      # 错误/紧急
    "red_dim":      "#dc2626",      # 错误暗色
    "blue":         "#3b82f6",      # 信息（蓝）
    "blue_dim":     "#2563eb",      # 信息暗色
    "purple":       "#8b5cf6",      # 次要紫
    "cyan":         "#06b6d4",      # 青色
    "yellow":       "#eab308",      # 黄色
    "pink":         "#ec4899",      # 粉色

    # 文字层次 — 深灰蓝系
    "text":         "#1e293b",      # 主文字（深灰蓝）
    "text_d":       "#64748b",      # 暗淡文字（中灰）
    "text_b":       "#0f172a",      # 标题文字（深黑蓝）
    "text_w":       "#ffffff",      # 纯白文字

    # 边框 — 浅灰蓝
    "border":       "#e2e8f0",      # 主边框
    "border_l":     "#cbd5e1",      # 亮边框（hover）

    # 表格
    "row_h":        "#f1f5f9",      # 行 hover
    "row_s":        "#e0f2fe",      # 行 selected
    "row_alt":      "#f8fafc",      # 交替行

    # 阴影 — 柔和轻阴影
    "shadow":       "rgba(0, 0, 0, 0.05)",
    "shadow_l":     "rgba(0, 0, 0, 0.1)",

    # 状态栏
    "statusbar":    "#ffffff",

    # 玻璃效果专用
    "glass_bg":     "rgba(255, 255, 255, 0.7)",
    "glass_border": "rgba(255, 255, 255, 0.4)",
    "glass_shadow": "0 8px 20px rgba(0, 0, 0, 0.03)",
}

# ── 暗色主题（深色玻璃质感） ────────────────────────────────
DARK_THEME: dict[str, str] = {
    "bg":           "#0f172a",      # 深蓝黑
    "bg_secondary": "#1e293b",      # 次级背景
    "sidebar":      "#1e293b",      # 侧边栏
    "sidebar_h":    "#334155",      # 侧边栏 hover
    "sidebar_s":    "#3b5274",      # 侧边栏 selected
    "card":         "#1e293b",      # 卡片背景
    "card_h":       "#334155",      # 卡片 hover
    "input":        "#1e293b",      # 输入框背景

    "accent":       "#3b82f6",      # 主强调色（蓝）
    "accent_l":     "#60a5fa",      # 强调色 hover
    "accent_dim":   "#2563eb",      # 强调色 pressed
    "accent_bg":    "#1e3a5f",      # 强调色背景

    "green":        "#34d399",      # 成功/完成
    "green_dim":    "#10b981",      # 成功暗色
    "orange":       "#fbbf24",      # 警告/待办
    "orange_dim":   "#f59e0b",      # 警告暗色
    "red":          "#f87171",      # 错误/紧急
    "red_dim":      "#ef4444",      # 错误暗色
    "blue":         "#60a5fa",      # 信息
    "blue_dim":     "#3b82f6",      # 信息暗色
    "purple":       "#a78bfa",      # 次要紫
    "cyan":         "#22d3ee",      # 青色
    "yellow":       "#fde047",      # 黄色
    "pink":         "#f472b6",      # 粉色

    "text":         "#e2e8f0",      # 主文字（浅灰白）
    "text_d":       "#94a3b8",      # 暗淡文字
    "text_b":       "#f1f5f9",      # 标题文字
    "text_w":       "#ffffff",      # 纯白文字

    "border":       "#334155",      # 主边框
    "border_l":     "#475569",      # 亮边框

    "row_h":        "#334155",      # 行 hover
    "row_s":        "#3b5274",      # 行 selected
    "row_alt":      "#1e293b",      # 交替行

    "shadow":       "rgba(0, 0, 0, 0.3)",
    "shadow_l":     "rgba(0, 0, 0, 0.5)",

    "statusbar":    "#1e293b",

    "glass_bg":     "rgba(30, 41, 59, 0.7)",
    "glass_border": "rgba(51, 65, 85, 0.5)",
    "glass_shadow": "0 8px 20px rgba(0, 0, 0, 0.2)",
}


class ThemeManager(QObject):
    """主题管理器 — 全局单例"""
    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._mode: str = "light"  # 默认浅色主题
        self._colors: dict[str, str] = LIGHT_THEME.copy()

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
        self._colors = (LIGHT_THEME if mode == "light" else DARK_THEME).copy()
        self.theme_changed.emit(mode)

    def toggle(self) -> str:
        new_mode = "dark" if self._mode == "light" else "light"
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

# ── 圆角常量 — 大圆角设计 ────────────────────────────────────
RADIUS = {
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
    "xl": "24px",
    "full": "9999px",
}


# ══════════════════════════════════════════════════════════════
#  QSS 模板 — 玻璃质感组件样式
# ══════════════════════════════════════════════════════════════

def BTN_PRIMARY_QSS() -> str:
    """主按钮 — 蓝色渐变实心，圆角40px"""
    t = get_theme()
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {t.get('accent')}, stop:1 {t.get('cyan')});
            color: {t.get('text_w')};
            border: none;
            border-radius: 40px;
            padding: 10px 24px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {t.get('accent_l')}, stop:1 {t.get('cyan')});
        }}
        QPushButton:pressed {{
            background: {t.get('accent_dim')};
        }}
        QPushButton:disabled {{
            background: {t.get('border')};
            color: {t.get('text_d')};
        }}
    """


def BTN_SECONDARY_QSS() -> str:
    """次级按钮 — 玻璃边框"""
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: {t.get('glass_bg')};
            color: {t.get('text')};
            border: 1px solid {t.get('glass_border')};
            border-radius: 40px;
            padding: 8px 20px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {t.get('card')};
            border-color: {t.get('accent')};
            color: {t.get('accent')};
        }}
    """


def BTN_DANGER_QSS() -> str:
    """危险按钮"""
    t = get_theme()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {t.get('red')};
            border: 1px solid {t.get('red')};
            border-radius: 40px;
            padding: 8px 20px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {t.get('red')};
            color: {t.get('text_w')};
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
            border-radius: 12px;
            padding: 6px 12px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {t.get('row_h')};
            color: {t.get('text')};
        }}
    """


def INPUT_QSS() -> str:
    """输入框 — 玻璃风格，圆角16px"""
    t = get_theme()
    return f"""
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {t.get('input')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: 16px;
            padding: 10px 16px;
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
    """下拉框 — 圆角16px"""
    t = get_theme()
    return f"""
        QComboBox {{
            background-color: {t.get('input')};
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: 16px;
            padding: 8px 16px;
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
            border-radius: 12px;
            padding: 4px;
            selection-background-color: {t.get('accent_bg')};
            selection-color: {t.get('accent')};
        }}
        QComboBox QAbstractItemView::item {{
            padding: 8px 12px;
            border-radius: 8px;
            min-height: 28px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {t.get('row_h')};
        }}
    """


def TABLE_QSS() -> str:
    """表格 — 玻璃风格"""
    t = get_theme()
    return f"""
        QTableWidget {{
            background-color: transparent;
            color: {t.get('text')};
            border: 1px solid {t.get('border')};
            border-radius: 16px;
            gridline-color: {t.get('border')};
            font-size: 13px;
        }}
        QTableWidget::item {{
            padding: 10px 12px;
            border-bottom: 1px solid transparent;
        }}
        QTableWidget::item:hover {{
            background-color: {t.get('row_h')};
        }}
        QTableWidget::item:selected {{
            background-color: {t.get('row_s')};
            color: {t.get('accent')};
        }}
        QHeaderView::section {{
            background-color: transparent;
            color: {t.get('text_d')};
            border: none;
            border-bottom: 2px solid {t.get('border')};
            padding: 12px;
            font-weight: 600;
            font-size: 12px;
        }}
    """


def TAB_QSS() -> str:
    """Tab 页签 — 圆角风格"""
    t = get_theme()
    return f"""
        QTabWidget::pane {{
            border: 1px solid {t.get('border')};
            border-radius: 16px;
            background-color: transparent;
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
            font-weight: 600;
        }}
        QTabBar::tab:hover {{
            color: {t.get('text')};
        }}
    """


def SCROLLBAR_QSS() -> str:
    """滚动条 — 细圆风格"""
    t = get_theme()
    return f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t.get('border')};
            border-radius: 3px;
            min-height: 40px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t.get('text_d')};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 6px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {t.get('border')};
            border-radius: 3px;
            min-width: 40px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {t.get('text_d')};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
    """


def LIST_WIDGET_QSS() -> str:
    """列表组件"""
    t = get_theme()
    return f"""
        QListWidget {{
            background-color: transparent;
            border: none;
            font-size: 13px;
        }}
        QListWidget::item {{
            padding: 10px 14px;
            border-radius: 12px;
            color: {t.get('text')};
            margin: 2px 4px;
        }}
        QListWidget::item:hover {{
            background-color: {t.get('row_h')};
        }}
        QListWidget::item:selected {{
            background-color: {t.get('row_s')};
            color: {t.get('accent')};
            font-weight: 600;
        }}
    """


def CARD_QSS() -> str:
    """卡片容器 — 玻璃质感"""
    t = get_theme()
    return f"""
        QFrame {{
            background-color: {t.get('card')};
            border: 1px solid {t.get('border')};
            border-radius: 24px;
        }}
        QFrame:hover {{
            border-color: {t.get('border_l')};
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
            border-radius: 24px;
            border-left: 3px solid {color};
        }}
        QFrame:hover {{
            border-color: {t.get('border_l')};
            border-left-color: {color};
        }}
    """


def GROUPBOX_QSS() -> str:
    """分组框 — 玻璃风格"""
    t = get_theme()
    return f"""
        QGroupBox {{
            background-color: {t.get('card')};
            border: 1px solid {t.get('border')};
            border-radius: 24px;
            margin-top: 14px;
            padding: 24px 16px 16px 16px;
            font-weight: 600;
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
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 12px;
        }}
    """
