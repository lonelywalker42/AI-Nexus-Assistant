"""主窗口框架 — 侧边栏导航 + QStackedWidget 页面切换 + 系统托盘"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QStackedWidget, QSystemTrayIcon,
    QMenu, QMessageBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction

from app.ui.theme import get_theme, SCROLLBAR_QSS


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
        self._apply_style()

        # 监听主题切换
        self._theme.theme_changed.connect(self._on_theme_changed)

    def _setup_ui(self):
        """构建 UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 侧边栏 ────────────────────────────────────────
        self._sidebar = QWidget()
        self._sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo 区域
        logo_frame = QWidget()
        logo_frame.setFixedHeight(72)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 12, 16, 8)
        title = QLabel("🧠 AI Nexus")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        subtitle = QLabel("个人科研助手")
        subtitle.setFont(QFont("Microsoft YaHei", 8))
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
            }}
            QListWidget::item {{
                padding: 12px 16px;
                color: {self._theme.get('text_d')};
                border-left: 3px solid transparent;
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background-color: {self._theme.get('sidebar_h')};
                color: {self._theme.get('text')};
            }}
            QListWidget::item:selected {{
                background-color: {self._theme.get('sidebar_s')};
                color: {self._theme.get('accent')};
                border-left: 3px solid {self._theme.get('accent')};
                font-weight: bold;
            }}
        """)

        nav_items = [
            ("📋  任务与日程", True),
            ("📚  文献管理", True),
            ("🧪  试验管理", False),   # Phase 2
            ("🧠  知识库", False),      # Phase 2
            ("💬  AI 对话", False),     # Phase 2
            ("⚙️  设置", True),
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
        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version_label)
        sidebar_layout.addSpacing(8)

        layout.addWidget(self._sidebar)

        # ── 内容区域 ──────────────────────────────────────
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # 创建页面（Phase 1: 任务、文献、设置）
        self._init_pages()

    def _init_pages(self):
        """初始化所有页面"""
        # 占位页面（未实现的模块）
        def placeholder(title: str) -> QWidget:
            w = QWidget()
            l = QVBoxLayout(w)
            lbl = QLabel(f"🚧 {title}\n\n将在后续阶段实现")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Microsoft YaHei", 16))
            l.addWidget(lbl)
            return w

        # Phase 1 页面
        from app.ui.pages.task_page import TaskPage
        from app.ui.pages.literature_page import LiteraturePage
        from app.ui.pages.settings_page import SettingsPage

        self._pages = [
            TaskPage(),              # 0: 任务与日程
            LiteraturePage(),        # 1: 文献管理
            placeholder("试验管理"),  # 2: Phase 2
            placeholder("知识库"),    # 3: Phase 2
            placeholder("AI 对话"),   # 4: Phase 2
            SettingsPage(),          # 5: 设置
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
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self._theme.get('bg')};
            }}
            QWidget {{
                color: {self._theme.get('text')};
            }}
            QLabel {{
                color: {self._theme.get('text')};
            }}
            {SCROLLBAR_QSS()}
        """)

    def _on_theme_changed(self, mode: str):
        """主题切换回调"""
        self._apply_style()
        # 重新绘制托盘图标
        self._tray.setIcon(self._create_tray_icon())
