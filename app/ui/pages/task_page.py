"""任务与日程页面 — 日历视图 + 待办列表 + 统计"""

from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QRadioButton, QButtonGroup,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from app.ui.theme import get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, INPUT_QSS, COMBO_QSS, SCROLLBAR_QSS, RADIUS
from app.ui.widgets.calendar_widget import CalendarWidget
from app.ui.widgets.stat_card import StatCard
from app.db import get_session
from app.services import task_service


class TaskPage(QWidget):
    """任务与日程页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._selected_date = date.today().isoformat()
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 左侧：日历 + 统计 ──────────────────────────────
        left = QWidget()
        left.setFixedWidth(320)
        left.setStyleSheet(f"background-color: {t.get('sidebar')};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        # 日历
        self._calendar = CalendarWidget()
        self._calendar.clicked.connect(self._on_date_selected)
        self._calendar.currentPageChanged.connect(self._on_month_changed)
        left_layout.addWidget(self._calendar)

        # 跳转今日按钮
        today_btn = QPushButton("  跳转今日")
        today_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.get('accent_bg')};
                color: {t.get('accent')};
                border: 1px solid {t.get('accent')};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t.get('accent')};
                color: {t.get('text_w')};
            }}
        """)
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.clicked.connect(self._go_today)
        left_layout.addWidget(today_btn)

        # 统计卡片
        stats_row = QHBoxLayout()
        self._stat_total = StatCard("总待办", "0", accent=t.get('orange'), icon="📋")
        self._stat_done = StatCard("已完成", "0", accent=t.get('green'), icon="✅")
        stats_row.addWidget(self._stat_total)
        stats_row.addWidget(self._stat_done)
        left_layout.addLayout(stats_row)

        # 月度统计
        self._month_label = QLabel("")
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._month_label.setFont(QFont("Microsoft YaHei", 10))
        self._month_label.setStyleSheet(f"color: {t.get('text_d')};")
        left_layout.addWidget(self._month_label)

        left_layout.addStretch()
        main_layout.addWidget(left)

        # ── 右侧：待办列表 ─────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(24, 16, 24, 16)
        right_layout.setSpacing(12)

        # 日期标题
        self._date_title = QLabel(f"📅 {self._selected_date}")
        self._date_title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self._date_title.setStyleSheet(f"color: {t.get('text_b')};")
        right_layout.addWidget(self._date_title)

        # 添加任务区域
        add_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("添加新的待办事项...")
        self._input.setStyleSheet(INPUT_QSS())
        self._input.setFixedHeight(36)
        self._input.returnPressed.connect(self._add_task)
        add_row.addWidget(self._input, 1)

        self._priority_combo = QComboBox()
        self._priority_combo.addItems(["普通", "低", "高", "紧急"])
        self._priority_combo.setStyleSheet(COMBO_QSS())
        self._priority_combo.setFixedWidth(80)
        add_row.addWidget(self._priority_combo)

        add_btn = QPushButton("➕ 添加")
        add_btn.setStyleSheet(BTN_PRIMARY_QSS())
        add_btn.setFixedSize(80, 36)
        add_btn.clicked.connect(self._add_task)
        add_row.addWidget(add_btn)

        right_layout.addLayout(add_row)

        # 过滤器
        filter_row = QHBoxLayout()
        self._filter_group = QButtonGroup(self)
        for i, text in enumerate(["全部", "待办", "已完成"]):
            rb = QRadioButton(text)
            rb.setStyleSheet(f"""
                QRadioButton {{
                    color: {t.get('text')};
                    spacing: 6px;
                }}
                QRadioButton::indicator {{
                    width: 14px; height: 14px;
                    border-radius: 7px;
                    border: 1px solid {t.get('border')};
                    background-color: {t.get('input')};
                }}
                QRadioButton::indicator:checked {{
                    background-color: {t.get('accent')};
                    border-color: {t.get('accent')};
                }}
            """)
            self._filter_group.addButton(rb, i)
            filter_row.addWidget(rb)
            if i == 0:
                rb.setChecked(True)

        self._filter_group.idClicked.connect(self._refresh_list)
        filter_row.addStretch()
        right_layout.addLayout(filter_row)

        # 任务列表（滚动区域）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        right_layout.addWidget(scroll, 1)

        main_layout.addWidget(right, 1)

    def refresh(self):
        """刷新页面数据"""
        self._refresh_calendar()
        self._refresh_list()
        self._refresh_stats()

    def reapply_theme(self):
        """主题切换后重新应用样式"""
        self._theme = get_theme()
        t = self._theme
        # 重新设置子组件样式
        self.setStyleSheet(f"background-color: {t.get('bg')};")
        if hasattr(self, '_calendar'):
            self._calendar._theme = t
            self._calendar._apply_style()
        self._refresh_list()  # 重建任务卡片

    def _go_today(self):
        """跳转到今日"""
        today = QDate.currentDate()
        self._calendar.setSelectedDate(today)
        self._calendar.showToday()
        self._on_date_selected(today)

    def _on_month_changed(self, year: int, month: int):
        """日历月份切换时刷新标记"""
        self._refresh_calendar(year, month)

    def _on_date_selected(self, qdate: QDate):
        self._selected_date = qdate.toString("yyyy-MM-dd")
        self._date_title.setText(f"📅 {self._selected_date}")
        self._refresh_list()
        self._refresh_stats()
        self._refresh_calendar()

    def _refresh_calendar(self, year: int | None = None, month: int | None = None):
        """刷新日历标记 — 支持指定月份"""
        db = get_session()
        try:
            if year is None or month is None:
                # 使用当前显示的月份
                current_date = self._calendar.selectedDate()
                year, month = current_date.year(), current_date.month()
            start = f"{year:04d}-{month:02d}-01"
            if month == 12:
                end = f"{year + 1:04d}-01-01"
            else:
                end = f"{year:04d}-{month + 1:02d}-01"

            marks = task_service.get_dates_with_todos(db, start, end)
            self._calendar.set_date_marks(marks)
        finally:
            db.close()

    def _refresh_list(self):
        """刷新任务列表"""
        # 清空列表
        while self._list_layout.count() > 1:  # 保留 stretch
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        db = get_session()
        try:
            tasks = task_service.get_all_todos_by_date(db, self._selected_date)

            # 过滤
            filter_id = self._filter_group.checkedId()
            if filter_id == 1:
                tasks = [t for t in tasks if not t.completed]
            elif filter_id == 2:
                tasks = [t for t in tasks if t.completed]

            if not tasks:
                empty = QLabel("暂无待办事项")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty.setStyleSheet(f"color: {self._theme.get('text_d')}; padding: 40px;")
                self._list_layout.insertWidget(0, empty)
            else:
                for task in reversed(tasks):
                    card = self._create_task_card(task)
                    self._list_layout.insertWidget(0, card)
        finally:
            db.close()

    def _create_task_card(self, task) -> QFrame:
        """创建单个任务卡片"""
        t = self._theme
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['lg']};
                border-left: 3px solid {self._priority_color(task.priority)};
            }}
            QFrame:hover {{
                background-color: {t.get('card_h')};
                border-color: {t.get('border_l')};
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 完成按钮
        check = QPushButton("✓" if task.completed else "○")
        check.setFixedSize(32, 32)
        check.setCursor(Qt.CursorShape.PointingHandCursor)
        color = t.get('green') if task.completed else t.get('border')
        check.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: 2px solid {color};
                border-radius: 16px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {t.get('green')};
                color: {t.get('green')};
            }}
        """)
        check.clicked.connect(lambda _, tid=task.id: self._toggle_task(tid))
        layout.addWidget(check)

        # 内容
        content = QLabel(task.content)
        content.setWordWrap(True)
        font = QFont("Microsoft YaHei", 11)
        if task.completed:
            content.setStyleSheet(f"color: {t.get('text_d')}; text-decoration: line-through;")
        else:
            content.setStyleSheet(f"color: {t.get('text')};")
        content.setFont(font)
        layout.addWidget(content, 1)

        # 时间
        time_str = ""
        if task.completed and task.completed_at:
            time_str = f"完成于 {task.completed_at.strftime('%H:%M')}"
        elif task.created_at:
            time_str = f"创建于 {task.created_at.strftime('%H:%M')}"
        if time_str:
            time_label = QLabel(time_str)
            time_label.setFont(QFont("Microsoft YaHei", 8))
            time_label.setStyleSheet(f"color: {t.get('text_d')};")
            layout.addWidget(time_label)

        # 删除按钮
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.get('text_d')};
                border: none;
                border-radius: 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {t.get('red')};
                color: {t.get('text_w')};
            }}
        """)
        del_btn.clicked.connect(lambda _, tid=task.id: self._delete_task(tid))
        layout.addWidget(del_btn)

        return card

    def _priority_color(self, priority: str) -> str:
        colors = {
            "low": self._theme.get('text_d'),
            "normal": self._theme.get('accent'),
            "high": self._theme.get('orange'),
            "urgent": self._theme.get('red'),
        }
        return colors.get(priority, self._theme.get('accent'))

    def _refresh_stats(self):
        """刷新统计"""
        db = get_session()
        try:
            stats = task_service.get_task_stats(db, self._selected_date)
            self._stat_total.update_value(str(stats["total"]))
            self._stat_done.update_value(str(stats["done"]))

            # 月度统计
            parts = self._selected_date.split("-")
            year, month = int(parts[0]), int(parts[1])
            m_total, m_done = task_service.get_month_stats(db, year, month)
            if m_total > 0:
                pct = int(m_done / m_total * 100)
                self._month_label.setText(f"本月: {m_done}/{m_total} 已完成 ({pct}%)")
            else:
                self._month_label.setText("本月暂无待办")
        finally:
            db.close()

    def _add_task(self):
        content = self._input.text().strip()
        if not content:
            return

        priority_map = {0: "normal", 1: "low", 2: "high", 3: "urgent"}
        priority = priority_map.get(self._priority_combo.currentIndex(), "normal")

        db = get_session()
        try:
            task_service.add_standalone_task(db, self._selected_date, content, priority)
        finally:
            db.close()

        self._input.clear()
        self.refresh()

    def _toggle_task(self, task_id: str):
        db = get_session()
        try:
            task_service.toggle_complete(db, task_id)
        finally:
            db.close()
        self.refresh()

    def _delete_task(self, task_id: str):
        db = get_session()
        try:
            task_service.delete_task(db, task_id)
        finally:
            db.close()
        self.refresh()
