"""桌面时钟组件 — 基于 clock-1999 的辉光管/机械表，使用 QPainter 渲染

支持两种模式：
1. 嵌入模式：紧凑的 HH:MM 显示，嵌入状态栏
2. 浮动模式：独立无边框窗口，完整辉光管/机械表效果
"""

import math
from datetime import datetime
from PySide6.QtWidgets import QWidget, QApplication, QMenu
from PySide6.QtCore import Qt, QTimer, QPoint, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QRadialGradient, QAction

from app.ui.theme import get_theme


# ── 辉光管数字灯丝路径 (76×100 坐标系) ────────────────────────
_NX = {
    '0': [[(20,10),(10,20),(10,80),(20,90),(56,90),(66,80),(66,20),(56,10),(20,10)]],
    '1': [[(30,10),(38,10),(38,90),(30,90)]],
    '2': [[(10,10),(66,10),(66,45),(10,45),(10,90),(66,90)]],
    '3': [[(10,10),(66,10),(66,45),(38,45)],[(66,45),(66,90),(10,90)]],
    '4': [[(10,10),(10,45),(66,45)],[(66,10),(66,90)]],
    '5': [[(66,10),(10,10),(10,45),(66,45),(66,90),(10,90)]],
    '6': [[(66,10),(10,10),(10,90),(66,90),(66,45),(10,45)]],
    '7': [[(10,10),(66,10),(66,90)]],
    '8': [[(10,10),(66,10),(66,90),(10,90),(10,10)],[(10,45),(66,45)]],
    '9': [[(66,45),(10,45),(10,10),(66,10),(66,90)]],
    ':': [[(30,25),(46,25),(46,40),(30,40),(30,25)],[(30,60),(46,60),(46,75),(30,75),(30,60)]],
}


class ClockWidget(QWidget):
    """桌面时钟组件"""

    def __init__(self, compact: bool = False, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._compact = compact  # True = 紧凑模式（嵌入状态栏）
        self._mode = "nixie"  # "nixie" / "watch"
        self._glow = True

        if compact:
            self.setFixedSize(80, 24)
        else:
            self.setFixedSize(660, 200)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._drag_pos = None

        # 定时刷新
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)  # ~30 FPS

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._compact:
            self._paint_compact(painter)
        elif self._mode == "nixie":
            self._paint_nixie(painter)
        else:
            self._paint_watch(painter)

    def _paint_compact(self, painter: QPainter):
        """紧凑模式 — 状态栏嵌入"""
        t = self._theme
        now = datetime.now()
        text = now.strftime("%H:%M:%S")

        painter.setPen(QColor(t.get('text')))
        painter.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def _paint_nixie(self, painter: QPainter):
        """辉光管模式"""
        w, h = self.width(), self.height()
        scale = min(w / 660, h / 200)

        # 背景
        painter.fillRect(0, 0, w, h, QColor(15, 15, 25))

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")

        # 绘制 6 位数字 + 冒号
        digit_width = 76 * scale
        spacing = 10 * scale
        start_x = (w - (6 * digit_width + 2 * spacing * 3)) / 2
        start_y = 20 * scale

        x = start_x
        for i, ch in enumerate(time_str):
            self._draw_nixie_digit(painter, ch, x, start_y, scale)
            x += digit_width + spacing

        # 底部 LED 面板
        panel_y = start_y + 110 * scale
        painter.setPen(QColor(100, 100, 120))
        painter.setFont(QFont("Consolas", int(10 * scale)))
        date_text = now.strftime("%Y-%m-%d %A")
        painter.drawText(int(w / 2 - 100 * scale), int(panel_y), int(200 * scale), int(20 * scale),
                         Qt.AlignmentFlag.AlignCenter, date_text)

    def _draw_nixie_digit(self, painter: QPainter, ch: str, x: float, y: float, scale: float):
        """绘制单个辉光管数字"""
        paths = _NX.get(ch, _NX['0'])

        # 多层光效
        colors = [
            QColor(255, 106, 0, 30),   # 光晕
            QColor(255, 106, 0, 60),   # 中层
            QColor(255, 150, 50, 120), # 灯丝
            QColor(255, 200, 100, 200),# 热核
            QColor(255, 220, 150, 255),# 核心
        ]
        widths = [12, 8, 5, 3, 1.5]

        for path in paths:
            for layer, (color, width) in enumerate(zip(colors, widths)):
                pen = QPen(color, width * scale)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)

                for j in range(len(path) - 1):
                    x1 = x + path[j][0] * scale
                    y1 = y + path[j][1] * scale
                    x2 = x + path[j + 1][0] * scale
                    y2 = y + path[j + 1][1] * scale
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _paint_watch(self, painter: QPainter):
        """机械表模式"""
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 20

        # 表盘背景
        painter.setBrush(QColor(240, 240, 245))
        painter.setPen(QPen(QColor(180, 180, 190), 3))
        painter.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # 刻度
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            if i % 5 == 0:
                inner = r * 0.82
                outer = r * 0.92
                pen = QPen(QColor(60, 60, 70), 2.5)
            else:
                inner = r * 0.88
                outer = r * 0.92
                pen = QPen(QColor(150, 150, 160), 1)
            painter.setPen(pen)
            painter.drawLine(
                int(cx + inner * math.cos(angle)), int(cy + inner * math.sin(angle)),
                int(cx + outer * math.cos(angle)), int(cy + outer * math.sin(angle)),
            )

        # 时标
        painter.setPen(QColor(40, 40, 50))
        painter.setFont(QFont("Times New Roman", int(r * 0.12), QFont.Weight.Bold))
        for i in range(1, 13):
            angle = math.radians(i * 30 - 90)
            tx = cx + r * 0.72 * math.cos(angle)
            ty = cy + r * 0.72 * math.sin(angle)
            painter.drawText(int(tx - 12), int(ty - 10), 24, 20, Qt.AlignmentFlag.AlignCenter, str(i))

        # 品牌
        painter.setPen(QColor(100, 100, 110))
        painter.setFont(QFont("Times New Roman", int(r * 0.06)))
        painter.drawText(int(cx - 40), int(cy - r * 0.3), 80, 16, Qt.AlignmentFlag.AlignCenter, "NEXUS")
        painter.drawText(int(cx - 40), int(cy - r * 0.3 + 14), 80, 12, Qt.AlignmentFlag.AlignCenter, "AUTOMATIC")

        now = datetime.now()
        h_angle = math.radians((now.hour % 12 + now.minute / 60) * 30 - 90)
        m_angle = math.radians(now.minute * 6 - 90)
        s_angle = math.radians(now.second * 6 - 90)

        # 时针
        self._draw_hand(painter, cx, cy, h_angle, r * 0.5, 6, QColor(40, 40, 50))
        # 分针
        self._draw_hand(painter, cx, cy, m_angle, r * 0.7, 4, QColor(40, 40, 50))
        # 秒针
        self._draw_hand(painter, cx, cy, s_angle, r * 0.8, 1.5, QColor(200, 50, 50))

        # 中心点
        painter.setBrush(QColor(40, 40, 50))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - 5), int(cy - 5), 10, 10)

    def _draw_hand(self, painter: QPainter, cx: float, cy: float,
                   angle: float, length: float, width: float, color: QColor):
        """绘制表针"""
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        ex = cx + length * math.cos(angle)
        ey = cy + length * math.sin(angle)
        painter.drawLine(int(cx), int(cy), int(ex), int(ey))

    def mousePressEvent(self, event):
        if not self._compact and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if not self._compact and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if not self._compact:
            self._mode = "watch" if self._mode == "nixie" else "nixie"
            if self._mode == "watch":
                self.setFixedSize(480, 480)
            else:
                self.setFixedSize(660, 200)

    def contextMenuEvent(self, event):
        if self._compact:
            return
        menu = QMenu(self)
        nixie_action = QAction("辉光管模式", self)
        nixie_action.triggered.connect(lambda: self._switch_mode("nixie"))
        watch_action = QAction("机械表模式", self)
        watch_action.triggered.connect(lambda: self._switch_mode("watch"))
        close_action = QAction("关闭时钟", self)
        close_action.triggered.connect(self.close)

        menu.addAction(nixie_action)
        menu.addAction(watch_action)
        menu.addSeparator()
        menu.addAction(close_action)
        menu.exec(event.globalPos())

    def _switch_mode(self, mode: str):
        self._mode = mode
        if mode == "watch":
            self.setFixedSize(480, 480)
        else:
            self.setFixedSize(660, 200)


class FloatingClock(QWidget):
    """浮动时钟窗口 — 独立的无边框透明窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clock = ClockWidget(compact=False, parent=self)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(660, 200)

    def showEvent(self, event):
        self._clock.setGeometry(0, 0, self.width(), self.height())
