"""日历组件 — 带待办状态标记的 QCalendarWidget"""

from PySide6.QtWidgets import QCalendarWidget
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QPainter, QColor, QTextCharFormat, QFont
from app.ui.theme import get_theme


class CalendarWidget(QCalendarWidget):
    """自定义日历 — 在日期格子中绘制彩色圆点标记待办状态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._marks: dict[str, str] = {}  # {"2026-06-11": "pending"|"completed"}
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._apply_style()

    def set_date_marks(self, marks: dict[str, str]):
        """设置日期标记 {date_str: "pending"|"completed"}"""
        self._marks = marks
        self.updateCells()

    def _apply_style(self):
        t = self._theme
        self.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {t.get('card')};
                color: {t.get('text')};
                border: 1px solid {t.get('border')};
                border-radius: 8px;
            }}
            QCalendarWidget QToolButton {{
                color: {t.get('text')};
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {t.get('card_h')};
            }}
            QCalendarWidget QAbstractItemView {{
                selection-background-color: {t.get('accent')};
                selection-color: white;
                font-size: 12px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {t.get('sidebar')};
            }}
        """)

    def paintCell(self, painter: QPainter, rect, date: QDate):
        """重绘单元格 — 底部绘制圆点"""
        # 调用默认绘制
        super().paintCell(painter, rect, date)

        date_str = date.toString("yyyy-MM-dd")
        status = self._marks.get(date_str)
        if not status:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(self._theme.get('orange') if status == "pending" else self._theme.get('green'))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)

        # 在格子底部中央画一个小圆点
        cx = rect.center().x()
        cy = rect.bottom() - 6
        painter.drawEllipse(cx - 3, cy - 3, 6, 6)

        painter.restore()
