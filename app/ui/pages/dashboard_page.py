"""仪表盘页面 — 全局统计聚合 + 近期活动流 + 进度可视化"""

from datetime import date, datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.ui.theme import get_theme
from app.ui.widgets.stat_card import StatCard
from app.db import get_session
from app.services import task_service, experiment_service, knowledge_service


class DashboardPage(QWidget):
    """仪表盘页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 24, 36, 24)
        layout.setSpacing(20)

        # 标题
        header = QHBoxLayout()
        title = QLabel("📊 仪表盘")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {t.get('text_b')};")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t.get('text_d')};
                border: 1px solid {t.get('border')};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                border-color: {t.get('accent')};
                color: {t.get('accent')};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # ── 统计卡片网格 ─────────────────────────────────────
        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(16)
        content_layout.addLayout(self._stats_grid)

        # ── 近期活动 ─────────────────────────────────────────
        activity_label = QLabel("🕐 近期活动")
        activity_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        activity_label.setStyleSheet(f"color: {t.get('text_b')};")
        content_layout.addWidget(activity_label)

        self._activity_container = QVBoxLayout()
        self._activity_container.setSpacing(8)
        content_layout.addLayout(self._activity_container)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def refresh(self):
        """刷新仪表盘数据"""
        self._refresh_stats()
        self._refresh_activity()

    def _refresh_stats(self):
        """刷新统计卡片"""
        # 清空
        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = self._theme
        db = get_session()
        try:
            today = date.today().isoformat()

            # 任务统计
            task_stats = task_service.get_task_stats(db, today)
            m_total, m_done = task_service.get_month_stats(db, date.today().year, date.today().month)
            completion_rate = f"{int(m_done / m_total * 100)}%" if m_total > 0 else "0%"

            # 试验统计
            exp_stats = experiment_service.get_experiment_stats(db)

            # 知识库统计
            kb_stats = knowledge_service.get_card_stats(db)

            # 构建卡片
            cards = [
                ("📋 今日待办", str(task_stats["total"]), f"完成 {task_stats['done']}", t.get('orange')),
                ("✅ 月度完成率", completion_rate, f"{m_done}/{m_total} 本月", t.get('green')),
                ("📚 文献总数", str(kb_stats.get("total", 0)), "篇知识卡片", t.get('blue')),
                ("🧪 进行中试验", str(exp_stats.get("running", 0)), f"共 {exp_stats.get('total', 0)} 项", t.get('purple')),
                ("📊 规划中试验", str(exp_stats.get("planning", 0)), "项待启动", t.get('accent')),
                ("🧠 知识卡片", str(kb_stats.get("total", 0)), f"{kb_stats.get('tag_count', 0)} 个标签", t.get('green')),
            ]

            for i, (title, value, subtitle, accent) in enumerate(cards):
                row, col = divmod(i, 3)
                card = StatCard(title, value, subtitle, accent)
                self._stats_grid.addWidget(card, row, col)
        finally:
            db.close()

    def _refresh_activity(self):
        """刷新近期活动"""
        # 清空
        while self._activity_container.count():
            item = self._activity_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = self._theme
        db = get_session()
        try:
            activities = []

            # 最近完成的任务
            from app.models.task import Task
            recent_tasks = (
                db.query(Task)
                .filter(Task.completed == True, Task.completed_at.isnot(None))
                .order_by(Task.completed_at.desc())
                .limit(5)
                .all()
            )
            for task in recent_tasks:
                time_str = task.completed_at.strftime("%H:%M") if task.completed_at else ""
                activities.append(("✅", f"完成: {task.content[:40]}", time_str, t.get('green')))

            # 最近的搜索历史
            from app.models.search_history import SearchHistory
            recent_searches = (
                db.query(SearchHistory)
                .order_by(SearchHistory.created_at.desc())
                .limit(3)
                .all()
            )
            for s in recent_searches:
                type_icon = {"search": "🔍", "review": "📊", "topic": "💡"}.get(s.history_type, "📋")
                time_str = s.created_at.strftime("%H:%M")
                activities.append((type_icon, f"{s.history_type}: {s.query[:40]}", time_str, t.get('blue')))

            # 最近的试验
            from app.models.experiment import Experiment
            recent_exps = (
                db.query(Experiment)
                .order_by(Experiment.updated_at.desc())
                .limit(3)
                .all()
            )
            for exp in recent_exps:
                time_str = exp.updated_at.strftime("%H:%M") if exp.updated_at else ""
                activities.append(("🧪", f"试验: {exp.title[:40]} [{exp.status}]", time_str, t.get('purple')))

            if not activities:
                empty = QLabel("暂无近期活动")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty.setStyleSheet(f"color: {t.get('text_d')}; padding: 40px;")
                self._activity_container.addWidget(empty)
            else:
                # 按时间排序（简化：保持插入顺序）
                for icon, text, time_str, color in activities[:15]:
                    row = QFrame()
                    row.setStyleSheet(f"""
                        QFrame {{
                            background-color: {t.get('card')};
                            border: 1px solid {t.get('border')};
                            border-radius: 6px;
                            padding: 4px;
                        }}
                        QFrame:hover {{
                            background-color: {t.get('card_h')};
                        }}
                    """)
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(12, 8, 12, 8)

                    icon_label = QLabel(icon)
                    icon_label.setFixedWidth(24)
                    row_layout.addWidget(icon_label)

                    text_label = QLabel(text)
                    text_label.setStyleSheet(f"color: {t.get('text')};")
                    row_layout.addWidget(text_label, 1)

                    time_label = QLabel(time_str)
                    time_label.setStyleSheet(f"color: {t.get('text_d')};")
                    time_label.setFixedWidth(50)
                    row_layout.addWidget(time_label)

                    self._activity_container.addWidget(row)
        finally:
            db.close()
