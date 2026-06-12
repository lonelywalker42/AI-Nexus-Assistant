"""桌面时钟组件 — 辉光管/机械表双模式 + 番茄学习钟

模式:
1. compact=True  — 紧凑模式，嵌入状态栏，显示 HH:MM:SS
2. compact=False — 完整模式，浮动窗口，辉光管/机械表/番茄钟
"""

import math
from datetime import datetime
from PySide6.QtWidgets import QWidget, QMenu, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient, QRadialGradient, QAction

from app.ui.theme import get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS


# ── 辉光管数字灯丝路径 (76×100 坐标系) ────────────────────────
_NX = {
    '0': [[(20,10),(10,20),(10,80),(20,90),(56,90),(66,80),(66,20),(56,10),(20,10)]],
    '1': [[(33,10),(41,10),(41,90),(33,90)]],
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

# ── 辉光管颜色层 ─────────────────────────────────────────────
_NIXIE_COLORS = [
    (QColor(255, 106, 0, 25), 14),   # 光晕
    (QColor(255, 106, 0, 50), 10),   # 中层
    (QColor(255, 150, 50, 110), 6),  # 灯丝
    (QColor(255, 200, 100, 190), 3), # 热核
    (QColor(255, 230, 170, 255), 1), # 核心
]


class ClockWidget(QWidget):
    """桌面时钟组件"""

    def __init__(self, compact: bool = False, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._compact = compact
        self._mode = "nixie"  # nixie / watch / pomodoro
        self._drag_pos = None

        # 番茄钟状态
        self._pomodoro_state = "idle"  # idle / work / break
        self._pomodoro_seconds = 25 * 60  # 默认25分钟
        self._pomodoro_remaining = 25 * 60
        self._pomodoro_work_min = 25
        self._pomodoro_break_min = 5

        if compact:
            self.setFixedSize(90, 24)
        else:
            self.setFixedSize(660, 220)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 定时刷新
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

    def _tick(self):
        """定时器回调"""
        # 番茄钟倒计时
        if self._mode == "pomodoro" and self._pomodoro_state in ("work", "break"):
            self._pomodoro_remaining = max(0, self._pomodoro_remaining - 1)
            if self._pomodoro_remaining == 0:
                self._pomodoro_switch()
        self.update()

    def _pomodoro_switch(self):
        """番茄钟状态切换"""
        if self._pomodoro_state == "work":
            self._pomodoro_state = "break"
            self._pomodoro_remaining = self._pomodoro_break_min * 60
        elif self._pomodoro_state == "break":
            self._pomodoro_state = "work"
            self._pomodoro_remaining = self._pomodoro_work_min * 60

    def _pomodoro_toggle(self):
        """番茄钟开始/暂停"""
        if self._pomodoro_state == "idle":
            self._pomodoro_state = "work"
            self._pomodoro_remaining = self._pomodoro_work_min * 60
        else:
            self._pomodoro_state = "idle"

    def _pomodoro_reset(self):
        """番茄钟重置"""
        self._pomodoro_state = "idle"
        self._pomodoro_remaining = self._pomodoro_work_min * 60

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._compact:
            self._paint_compact(painter)
        elif self._mode == "nixie":
            self._paint_nixie(painter)
        elif self._mode == "watch":
            self._paint_watch(painter)
        else:
            self._paint_pomodoro(painter)

    def _paint_compact(self, painter: QPainter):
        """紧凑模式 — 状态栏"""
        t = self._theme
        now = datetime.now()
        text = now.strftime("%H:%M:%S")
        painter.setPen(QColor(t.get('text')))
        painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def _paint_nixie(self, painter: QPainter):
        """辉光管模式"""
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(12, 12, 20))

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        scale = min(w / 660, h / 220)

        # 绘制 8 个字符
        digit_w = 76 * scale
        spacing = 8 * scale
        total_w = len(time_str) * digit_w + (len(time_str) - 1) * spacing
        start_x = (w - total_w) / 2
        start_y = 25 * scale

        x = start_x
        for ch in time_str:
            self._draw_nixie_digit(painter, ch, x, start_y, scale)
            x += digit_w + spacing

        # 底部信息面板
        panel_y = start_y + 115 * scale
        painter.setPen(QColor(90, 100, 130))
        painter.setFont(QFont("Consolas", int(9 * scale)))
        date_text = now.strftime("%Y-%m-%d")
        painter.drawText(int(w / 2 - 80 * scale), int(panel_y), int(160 * scale), int(16 * scale),
                         Qt.AlignmentFlag.AlignCenter, date_text)

        # 星期
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        wd = weekdays[now.weekday()]
        painter.drawText(int(w / 2 - 30 * scale), int(panel_y + 14 * scale), int(60 * scale), int(14 * scale),
                         Qt.AlignmentFlag.AlignCenter, wd)

    def _draw_nixie_digit(self, painter: QPainter, ch: str, x: float, y: float, scale: float):
        """绘制单个辉光管数字"""
        paths = _NX.get(ch, _NX['0'])
        for path in paths:
            for color, width in _NIXIE_COLORS:
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

        # 表盘
        painter.setBrush(QColor(242, 242, 248))
        painter.setPen(QPen(QColor(180, 180, 190), 3))
        painter.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # 刻度
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            if i % 5 == 0:
                inner, outer, width = r * 0.82, r * 0.92, 2.5
                pen = QPen(QColor(50, 50, 60), width)
            else:
                inner, outer, width = r * 0.88, r * 0.92, 1
                pen = QPen(QColor(160, 160, 170), width)
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
        s_angle = math.radians((now.second + now.microsecond / 1e6) * 6 - 90)

        self._draw_hand(painter, cx, cy, h_angle, r * 0.5, 6, QColor(40, 40, 50))
        self._draw_hand(painter, cx, cy, m_angle, r * 0.7, 4, QColor(40, 40, 50))
        self._draw_hand(painter, cx, cy, s_angle, r * 0.8, 1.5, QColor(200, 50, 50))

        painter.setBrush(QColor(40, 40, 50))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - 5), int(cy - 5), 10, 10)

    def _draw_hand(self, painter, cx, cy, angle, length, width, color):
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        ex = cx + length * math.cos(angle)
        ey = cy + length * math.sin(angle)
        painter.drawLine(int(cx), int(cy), int(ex), int(ey))

    def _paint_pomodoro(self, painter: QPainter):
        """番茄学习钟模式"""
        w, h = self.width(), self.height()
        t = self._theme
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 40

        # 背景
        painter.fillRect(0, 0, w, h, QColor(12, 12, 20))

        # 颜色根据状态
        if self._pomodoro_state == "work":
            main_color = QColor(239, 107, 107)  # 红色 — 工作
            label_text = "工作中"
        elif self._pomodoro_state == "break":
            main_color = QColor(64, 199, 144)   # 绿色 — 休息
            label_text = "休息中"
        else:
            main_color = QColor(124, 106, 239)  # 紫色 — 空闲
            label_text = "番茄钟"

        # 外圈 — 进度环
        pen = QPen(QColor(50, 50, 70), 8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(int(cx - r), int(cy - r), int(2 * r), int(2 * r), 0, 360 * 16)

        # 进度
        if self._pomodoro_state != "idle":
            total = (self._pomodoro_work_min if self._pomodoro_state == "work" else self._pomodoro_break_min) * 60
            progress = 1 - self._pomodoro_remaining / total
            span_angle = int(progress * 360 * 16)
            pen = QPen(main_color, 8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(int(cx - r), int(cy - r), int(2 * r), int(2 * r),
                            90 * 16, -span_angle)

        # 倒计时数字
        mins = self._pomodoro_remaining // 60
        secs = self._pomodoro_remaining % 60
        time_text = f"{mins:02d}:{secs:02d}"

        painter.setPen(main_color)
        painter.setFont(QFont("Consolas", 48, QFont.Weight.Bold))
        painter.drawText(int(cx - 100), int(cy - 40), 200, 70, Qt.AlignmentFlag.AlignCenter, time_text)

        # 状态标签
        painter.setPen(QColor(150, 150, 180))
        painter.setFont(QFont("Microsoft YaHei", 14))
        painter.drawText(int(cx - 60), int(cy + 30), 120, 30, Qt.AlignmentFlag.AlignCenter, label_text)

        # 底部提示
        painter.setPen(QColor(80, 80, 110))
        painter.setFont(QFont("Microsoft YaHei", 10))
        hint = "右键菜单: 开始/暂停 | 双击切换模式"
        painter.drawText(int(cx - 150), int(cy + 60), 300, 20, Qt.AlignmentFlag.AlignCenter, hint)

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
            modes = ["nixie", "watch", "pomodoro"]
            idx = modes.index(self._mode) if self._mode in modes else 0
            self._mode = modes[(idx + 1) % 3]
            if self._mode == "watch":
                self.setFixedSize(480, 480)
            else:
                self.setFixedSize(660, 220)

    def contextMenuEvent(self, event):
        if self._compact:
            return
        menu = QMenu(self)

        # 模式切换
        nixie_action = QAction("辉光管模式", self)
        nixie_action.triggered.connect(lambda: self._switch_mode("nixie"))
        watch_action = QAction("机械表模式", self)
        watch_action.triggered.connect(lambda: self._switch_mode("watch"))
        pomodoro_action = QAction("番茄学习钟", self)
        pomodoro_action.triggered.connect(lambda: self._switch_mode("pomodoro"))

        menu.addAction(nixie_action)
        menu.addAction(watch_action)
        menu.addAction(pomodoro_action)

        # 番茄钟控制
        if self._mode == "pomodoro":
            menu.addSeparator()
            if self._pomodoro_state == "idle":
                start_action = QAction("开始番茄钟", self)
                start_action.triggered.connect(self._pomodoro_toggle)
                menu.addAction(start_action)
            else:
                pause_action = QAction("暂停", self)
                pause_action.triggered.connect(self._pomodoro_toggle)
                menu.addAction(pause_action)

            reset_action = QAction("重置", self)
            reset_action.triggered.connect(self._pomodoro_reset)
            menu.addAction(reset_action)

            menu.addSeparator()
            for mins in [15, 25, 30, 45]:
                action = QAction(f"工作 {mins} 分钟", self)
                action.triggered.connect(lambda _, m=mins: self._set_work_time(m))
                menu.addAction(action)

        menu.addSeparator()
        close_action = QAction("关闭时钟", self)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)

        menu.exec(event.globalPosition().toPoint())

    def _switch_mode(self, mode: str):
        self._mode = mode
        if mode == "watch":
            self.setFixedSize(480, 480)
        else:
            self.setFixedSize(660, 220)

    def _set_work_time(self, minutes: int):
        self._pomodoro_work_min = minutes
        self._pomodoro_remaining = minutes * 60
        self._pomodoro_state = "idle"
