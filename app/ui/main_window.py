"""主窗口框架 — 侧边栏导航 + QStackedWidget 页面切换 + 系统托盘 + 时钟 + 命令面板"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QStackedWidget, QSystemTrayIcon,
    QMenu, QMessageBox, QStatusBar, QPushButton,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QKeySequence, QShortcut

from app.ui.theme import get_theme, SCROLLBAR_QSS, LIST_WIDGET_QSS


class MainWindow(QMainWindow):
    """AI Nexus Assistant 主窗口 — 无边框可拖拽"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Nexus Assistant")
        self.setMinimumSize(1200, 750)
        self.resize(1360, 860)

        # 无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._theme = get_theme()
        self._pages: list[QWidget] = []
        self._drag_pos = None
        self._floating_clock = None  # 浮动时钟窗口
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
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 自定义标题栏（无边框窗口拖拽 + 控制按钮） ───────
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet(f"""
            background-color: {self._theme.get('sidebar')};
            border-bottom: 1px solid {self._theme.get('border')};
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(12, 0, 12, 0)

        # 标题文字
        title_text = QLabel("AI Nexus Assistant")
        title_text.setFont(QFont("Inter", 10))
        title_text.setStyleSheet(f"color: {self._theme.get('text_d')};")
        title_bar_layout.addWidget(title_text)
        title_bar_layout.addStretch()

        # 最小化按钮
        min_btn = QPushButton("—")
        min_btn.setFixedSize(32, 28)
        min_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self._theme.get('text_d')};
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self._theme.get('row_h')};
            }}
        """)
        min_btn.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(min_btn)

        # 最大化/还原按钮
        self._max_btn = QPushButton("□")
        self._max_btn.setFixedSize(32, 28)
        self._max_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self._theme.get('text_d')};
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self._theme.get('row_h')};
            }}
        """)
        self._max_btn.clicked.connect(self._toggle_maximize)
        title_bar_layout.addWidget(self._max_btn)

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self._theme.get('text_d')};
                border: none;
                border-radius: 6px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {self._theme.get('red')};
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.close)
        title_bar_layout.addWidget(close_btn)

        # 标题栏拖拽
        title_bar.mousePressEvent = self._title_mouse_press
        title_bar.mouseMoveEvent = self._title_mouse_move
        title_bar.mouseReleaseEvent = self._title_mouse_release

        main_layout.addWidget(title_bar)

        # ── 主内容区域 ─────────────────────────────────────
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 侧边栏（玻璃质感） ─────────────────────────────
        self._sidebar = QWidget()
        self._sidebar.setFixedWidth(260)
        self._sidebar.setStyleSheet(f"""
            QWidget {{
                background-color: {self._theme.get('sidebar')};
                border-right: 1px solid {self._theme.get('border')};
            }}
        """)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo 区域（清新风格）
        logo_frame = QWidget()
        logo_frame.setFixedHeight(80)
        logo_frame.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border-bottom: 1px solid {self._theme.get('border')};
            }}
        """)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(24, 18, 24, 14)
        title = QLabel("NEXUS")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self._theme.get('accent')}; letter-spacing: 3px;")
        subtitle = QLabel("AI 科研助手")
        subtitle.setFont(QFont("Inter", 10))
        subtitle.setStyleSheet(f"color: {self._theme.get('text_d')};")
        logo_layout.addWidget(title)
        logo_layout.addWidget(subtitle)
        sidebar_layout.addWidget(logo_frame)

        # 导航列表（圆角玻璃风格）
        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                padding: 12px 10px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                color: {self._theme.get('text_d')};
                border-left: 3px solid transparent;
                border-radius: 12px;
                font-size: 13px;
                margin: 2px 0;
            }}
            QListWidget::item:hover {{
                background-color: {self._theme.get('row_h')};
                color: {self._theme.get('text')};
            }}
            QListWidget::item:selected {{
                background-color: {self._theme.get('accent_bg')};
                color: {self._theme.get('accent')};
                border-left: 3px solid {self._theme.get('accent')};
                font-weight: 600;
            }}
        """)

        # 导航项（index 与 _pages 一一对应，不含分隔符）
        nav_items = [
            ("◆  仪表盘", True),
            ("◇  任务与日程", True),
            ("◈  文献管理", True),
            ("◉  试验管理", True),
            ("◎  知识库", True),
            ("◊  AI 对话", True),
            ("○  设置", True),
        ]

        # 添加分组标签 + 导航项
        group_labels = {
            0: "总览",
            2: "研究",
            5: "系统",
        }
        for i, (text, enabled) in enumerate(nav_items):
            # 在指定位置插入分组标签
            if i in group_labels:
                label_item = QListWidgetItem(f"  {group_labels[i]}")
                label_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 不可选中
                label_item.setForeground(QColor(self._theme.get('text_d')))
                label_item.setFont(QFont("Inter", 9))
                self._nav_list.addItem(label_item)

            item = QListWidgetItem(text)
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(QColor(self._theme.get('text_d')))
            self._nav_list.addItem(item)

        # 建立行号 → 页面索引的映射（跳过分组标签行）
        self._nav_row_to_page: dict[int, int] = {}
        page_idx = 0
        for row in range(self._nav_list.count()):
            item = self._nav_list.item(row)
            if item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self._nav_row_to_page[row] = page_idx
                page_idx += 1

        self._nav_list.currentRowChanged.connect(self._switch_page)
        sidebar_layout.addWidget(self._nav_list, 1)

        # 底部版本标签（药丸样式）
        version_label = QLabel("v0.3.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"""
            color: {self._theme.get('text_d')};
            font-size: 11px;
            padding: 6px 12px;
            border-top: 1px solid {self._theme.get('border')};
        """)
        sidebar_layout.addWidget(version_label)

        layout.addWidget(self._sidebar)

        # ── 内容区域 ──────────────────────────────────────
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        main_layout.addWidget(content)

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

    def _switch_page(self, row: int):
        """切换页面 — 通过行号映射到页面索引"""
        page_idx = self._nav_row_to_page.get(row, -1)
        if 0 <= page_idx < len(self._pages):
            self._stack.setCurrentIndex(page_idx)
            page = self._pages[page_idx]
            if hasattr(page, "refresh"):
                page.refresh()

    def _setup_tray(self):
        """系统托盘"""
        icon = self._create_tray_icon()
        self._tray = QSystemTrayIcon(icon, self)

        menu = QMenu()
        open_action = QAction("打开主窗口", self)
        open_action.triggered.connect(self._show_window)
        clock_action = QAction("显示浮动时钟", self)
        clock_action.triggered.connect(self._launch_floating_clock)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)

        menu.addAction(open_action)
        menu.addAction(clock_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.setToolTip("AI Nexus Assistant")
        self._tray.show()

    def _create_tray_icon(self) -> QIcon:
        """绘制精致托盘图标 — 蓝紫渐变 + 神经网络风格"""
        from PySide6.QtGui import QRadialGradient, QLinearGradient, QBrush, QPen

        icon = QIcon()
        for size in [16, 32, 48, 64, 128]:
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            s = size / 64.0  # 缩放因子

            # 外层柔光
            glow = QRadialGradient(32*s, 32*s, 34*s)
            glow.setColorAt(0.5, QColor(124, 106, 239, 25))
            glow.setColorAt(1.0, QColor(124, 106, 239, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, size, size)

            # 主体圆 — 蓝紫渐变
            grad = QLinearGradient(8*s, 8*s, 56*s, 56*s)
            grad.setColorAt(0.0, QColor(139, 124, 240))   # 亮紫
            grad.setColorAt(0.5, QColor(96, 165, 250))    # 蓝
            grad.setColorAt(1.0, QColor(59, 130, 246))    # 深蓝
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(6*s), int(6*s), int(52*s), int(52*s))

            # 内环高光
            highlight = QRadialGradient(24*s, 22*s, 20*s)
            highlight.setColorAt(0.0, QColor(255, 255, 255, 60))
            highlight.setColorAt(0.7, QColor(255, 255, 255, 10))
            highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(highlight))
            painter.drawEllipse(int(10*s), int(10*s), int(44*s), int(38*s))

            # 文字 "N"
            if size >= 32:
                font_size = int(22 * s)
                painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
                # 阴影
                painter.setPen(QColor(0, 0, 0, 50))
                painter.drawText(pixmap.rect().adjusted(1, 2, 1, 2), Qt.AlignmentFlag.AlignCenter, "N")
                # 本体
                painter.setPen(QColor(255, 255, 255, 250))
                painter.drawText(pixmap.rect().adjusted(0, 1, 0, 1), Qt.AlignmentFlag.AlignCenter, "N")

            painter.end()
            icon.addPixmap(pixmap)

        return icon

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
        """主题切换回调 — 重新渲染所有组件"""
        self._apply_style()
        self._tray.setIcon(self._create_tray_icon())

        # 重新设置侧边栏样式
        self._sidebar.setStyleSheet(f"""
            QWidget {{
                background-color: {self._theme.get('sidebar')};
                border-right: 1px solid {self._theme.get('border')};
            }}
        """)

        # 重新设置导航列表样式
        self._nav_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
                padding: 12px 10px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                color: {self._theme.get('text_d')};
                border-left: 3px solid transparent;
                border-radius: 12px;
                font-size: 13px;
                margin: 2px 0;
            }}
            QListWidget::item:hover {{
                background-color: {self._theme.get('row_h')};
                color: {self._theme.get('text')};
            }}
            QListWidget::item:selected {{
                background-color: {self._theme.get('accent_bg')};
                color: {self._theme.get('accent')};
                border-left: 3px solid {self._theme.get('accent')};
                font-weight: 600;
            }}
        """)

        # 重新设置状态栏样式
        if hasattr(self, 'statusBar'):
            sb = self.statusBar()
            if sb:
                sb.setStyleSheet(f"""
                    QStatusBar {{
                        background-color: {self._theme.get('statusbar')};
                        color: {self._theme.get('text_d')};
                        border-top: 1px solid {self._theme.get('border')};
                        padding: 6px 16px;
                        font-size: 12px;
                    }}
                """)

        # 刷新所有页面的主题
        for page in self._pages:
            if hasattr(page, 'reapply_theme'):
                page.reapply_theme()

        # 刷新当前页面
        current_row = self._nav_list.currentRow()
        if current_row >= 0:
            self._switch_page(current_row)

    def _setup_status_bar(self):
        """状态栏 — 时钟 + 信息"""
        from app.ui.widgets.clock_widget import ClockWidget

        status_bar = QStatusBar()
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {self._theme.get('statusbar')};
                color: {self._theme.get('text_d')};
                border-top: 1px solid {self._theme.get('border')};
                padding: 6px 16px;
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
        # 找到页面索引对应的行号
        for row, idx in self._nav_row_to_page.items():
            if idx == page_index:
                self._nav_list.setCurrentRow(row)
                self._switch_page(row)
                return

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

    # ── 无边框窗口拖拽 ──────────────────────────────────────

    def _title_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def _title_mouse_move(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _title_mouse_release(self, event):
        self._drag_pos = None

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self._max_btn.setText("□")
        else:
            self.showMaximized()
            self._max_btn.setText("❐")

    # ── 浮动时钟 ────────────────────────────────────────────

    def _launch_floating_clock(self):
        """启动独立的 clock-1999 浮动时钟窗口"""
        if self._floating_clock is not None and self._floating_clock.isVisible():
            self._floating_clock.activateWindow()
            return

        from app.ui.widgets.clock_widget import ClockWidget
        self._floating_clock = ClockWidget(compact=False)
        self._floating_clock.setWindowTitle("Clock")
        self._floating_clock.show()
