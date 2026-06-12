"""主窗口框架 — 侧边栏导航 + QStackedWidget 页面切换 + 系统托盘 + 时钟 + 命令面板"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QStackedWidget, QSystemTrayIcon,
    QMenu, QMessageBox, QStatusBar,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QKeySequence, QShortcut

from app.ui.theme import get_theme, SCROLLBAR_QSS, LIST_WIDGET_QSS


class MainWindow(QMainWindow):
    """AI Nexus Assistant 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Nexus Assistant")
        self.setMinimumSize(1200, 750)
        self.resize(1360, 860)

        self._theme = get_theme()
        self._pages: list[QWidget] = []
        self._setup_ui()
        self._setup_tray()
        self._setup_status_bar()
        self._setup_shortcuts()
        self._apply_style()

        # 监听主题切换
        self._theme.theme_changed.connect(self._on_theme_changed)

        # 自动备份
        self._auto_backup()

    def _setup_ui(self):
        """构建 UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 侧边栏 ────────────────────────────────────────
        self._sidebar = QWidget()
        self._sidebar.setFixedWidth(220)
        self._sidebar.setStyleSheet(f"""
            QWidget {{
                background-color: {self._theme.get('sidebar')};
                border-right: 1px solid {self._theme.get('border')};
            }}
        """)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo 区域
        logo_frame = QWidget()
        logo_frame.setFixedHeight(72)
        logo_frame.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border-bottom: 1px solid {self._theme.get('border')};
            }}
        """)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(20, 16, 20, 12)
        title = QLabel("NEXUS")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self._theme.get('accent_l')}; letter-spacing: 2px;")
        subtitle = QLabel("个人科研助手")
        subtitle.setFont(QFont("Microsoft YaHei", 9))
        subtitle.setStyleSheet(f"color: {self._theme.get('text_d')};")
        logo_layout.addWidget(title)
        logo_layout.addWidget(subtitle)
        sidebar_layout.addWidget(logo_frame)

        # 导航列表
        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                padding: 8px 6px;
            }}
            QListWidget::item {{
                padding: 11px 16px;
                color: {self._theme.get('text_d')};
                border-left: 3px solid transparent;
                border-radius: 0 6px 6px 0;
                font-size: 13px;
                margin: 1px 0;
            }}
            QListWidget::item:hover {{
                background-color: {self._theme.get('sidebar_h')};
                color: {self._theme.get('text')};
                border-left-color: {self._theme.get('border_l')};
            }}
            QListWidget::item:selected {{
                background-color: {self._theme.get('sidebar_s')};
                color: {self._theme.get('accent_l')};
                border-left: 3px solid {self._theme.get('accent')};
                font-weight: bold;
            }}
        """)

        nav_items = [
            ("◆  仪表盘", True),
            ("◇  任务与日程", True),
            ("◈  文献管理", True),
            ("◉  试验管理", True),
            ("◎  知识库", True),
            ("◊  AI 对话", True),
            ("○  设置", True),
        ]
        for text, enabled in nav_items:
            item = QListWidgetItem(text)
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(QColor(self._theme.get('text_d')))
            self._nav_list.addItem(item)

        self._nav_list.currentRowChanged.connect(self._switch_page)
        sidebar_layout.addWidget(self._nav_list, 1)

        # 底部版本标签
        version_label = QLabel("v0.3.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"""
            color: {self._theme.get('text_d')};
            font-size: 11px;
            padding: 8px;
            border-top: 1px solid {self._theme.get('border')};
        """)
        sidebar_layout.addWidget(version_label)

        layout.addWidget(self._sidebar)

        # ── 内容区域 ──────────────────────────────────────
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # 创建页面（Phase 1: 任务、文献、设置）
        self._init_pages()

    def _init_pages(self):
        """初始化所有页面"""
        from app.ui.pages.dashboard_page import DashboardPage
        from app.ui.pages.task_page import TaskPage
        from app.ui.pages.literature_page import LiteraturePage
        from app.ui.pages.experiment_page import ExperimentPage
        from app.ui.pages.knowledge_page import KnowledgePage
        from app.ui.pages.chat_page import ChatPage
        from app.ui.pages.settings_page import SettingsPage

        self._pages = [
            DashboardPage(),         # 0: 仪表盘
            TaskPage(),              # 1: 任务与日程
            LiteraturePage(),        # 2: 文献管理
            ExperimentPage(),        # 3: 试验管理
            KnowledgePage(),         # 4: 知识库
            ChatPage(),              # 5: AI 对话
            SettingsPage(),          # 6: 设置
        ]

        for page in self._pages:
            self._stack.addWidget(page)

    def _switch_page(self, index: int):
        """切换页面"""
        if 0 <= index < len(self._pages):
            self._stack.setCurrentIndex(index)
            page = self._pages[index]
            if hasattr(page, "refresh"):
                page.refresh()

    def _setup_tray(self):
        """系统托盘"""
        icon = self._create_tray_icon()
        self._tray = QSystemTrayIcon(icon, self)

        menu = QMenu()
        open_action = QAction("打开主窗口", self)
        open_action.triggered.connect(self._show_window)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)

        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.setToolTip("AI Nexus Assistant")
        self._tray.show()

    def _create_tray_icon(self) -> QIcon:
        """绘制托盘图标"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景圆
        painter.setBrush(QColor(self._theme.get('accent')))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56)

        # 文字
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "N")

        painter.end()
        return QIcon(pixmap)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self):
        self._tray.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def closeEvent(self, event):
        """关闭时最小化到托盘"""
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "AI Nexus Assistant",
            "已最小化到系统托盘",
            QSystemTrayIcon.MessageIcon.Information,
            1500,
        )

    def _apply_style(self):
        """应用全局样式"""
        from app.ui.theme import TOOLTIP_QSS
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self._theme.get('bg')};
            }}
            QWidget {{
                color: {self._theme.get('text')};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QLabel {{
                color: {self._theme.get('text')};
            }}
            {SCROLLBAR_QSS()}
            {TOOLTIP_QSS()}
        """)

    def _on_theme_changed(self, mode: str):
        """主题切换回调"""
        self._apply_style()
        # 重新绘制托盘图标
        self._tray.setIcon(self._create_tray_icon())

    def _setup_status_bar(self):
        """状态栏 — 时钟 + 信息"""
        from app.ui.widgets.clock_widget import ClockWidget

        status_bar = QStatusBar()
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {self._theme.get('statusbar')};
                color: {self._theme.get('text_d')};
                border-top: 1px solid {self._theme.get('border')};
                padding: 4px 12px;
                font-size: 12px;
            }}
        """)

        # 左侧信息
        info_label = QLabel("  AI Nexus Assistant")
        info_label.setStyleSheet(f"color: {self._theme.get('text_d')};")
        status_bar.addWidget(info_label)

        # 右侧时钟
        self._clock = ClockWidget(compact=True)
        status_bar.addPermanentWidget(self._clock)

        self.setStatusBar(status_bar)

    def _setup_shortcuts(self):
        """快捷键"""
        # Ctrl+K: 命令面板
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self._show_command_palette)

    def _show_command_palette(self):
        """显示命令面板"""
        from app.ui.dialogs.command_palette import CommandPalette
        palette = CommandPalette(self)
        palette.navigate.connect(self._navigate_to)
        palette.exec()

    def _navigate_to(self, page_index: int, item_id: str):
        """从命令面板导航到指定页面"""
        if 0 <= page_index < len(self._pages):
            self._nav_list.setCurrentRow(page_index)
            self._switch_page(page_index)

    def _auto_backup(self):
        """启动时自动备份"""
        try:
            from app.services.backup_service import auto_backup
            result = auto_backup()
            if result.get("created"):
                print(f"[Backup] Created: {result['created']}")
            if result.get("cleaned", 0) > 0:
                print(f"[Backup] Cleaned {result['cleaned']} old backups")
        except Exception as e:
            print(f"[Backup] Error: {e}")
