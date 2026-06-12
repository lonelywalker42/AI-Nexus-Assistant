"""AI对话页面 — 流式对话 + thinking折叠 + 写作辅助 + 跨模块联动"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QSplitter, QListWidget, QListWidgetItem, QFrame,
    QComboBox, QScrollArea, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from app.ui.theme import (
    get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, BTN_DANGER_QSS,
    BTN_GHOST_QSS, INPUT_QSS, COMBO_QSS, RADIUS,
)
from app.db import get_session
from app.services import chat_service
from app.ai.router import AIRouter


class _StreamWorker(QThread):
    """AI 流式对话工作线程"""
    thinking_chunk = Signal(str)
    content_chunk = Signal(str)
    finished = Signal(str, str)
    error = Signal(str)

    def __init__(self, ai_router: AIRouter, messages: list[dict],
                 purpose: str = "chat", model_id: str | None = None):
        super().__init__()
        self._router = ai_router
        self._messages = messages
        self._purpose = purpose
        self._model_id = model_id

    def run(self):
        try:
            full_thinking = ""
            full_content = ""
            for chunk in self._router.stream_chat(
                self._messages, purpose=self._purpose, model_id=self._model_id
            ):
                if chunk["type"] == "thinking":
                    full_thinking += chunk["data"]
                    self.thinking_chunk.emit(chunk["data"])
                elif chunk["type"] == "content":
                    full_content += chunk["data"]
                    self.content_chunk.emit(chunk["data"])
            self.finished.emit(full_thinking, full_content)
        except Exception as e:
            self.error.emit(str(e))


class ChatPage(QWidget):
    """AI对话页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._ai_router = AIRouter()
        self._current_session_id: str | None = None
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 左侧：会话管理面板 ─────────────────────────────
        left = QWidget()
        left.setFixedWidth(260)
        left.setStyleSheet(f"""
            background-color: {t.get('sidebar')};
            border-right: 1px solid {t.get('border')};
        """)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        # 标题
        header = QLabel("AI 对话")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {t.get('text_b')};")
        left_layout.addWidget(header)

        # 模型选择
        model_frame = QFrame()
        model_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['md']};
                padding: 4px;
            }}
        """)
        model_layout = QVBoxLayout(model_frame)
        model_layout.setContentsMargins(8, 8, 8, 8)
        model_layout.setSpacing(4)

        model_label = QLabel("模型")
        model_label.setFont(QFont("Inter", 9))
        model_label.setStyleSheet(f"color: {t.get('text_d')};")
        model_layout.addWidget(model_label)

        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet(COMBO_QSS())
        self._refresh_models()
        model_layout.addWidget(self._model_combo)
        left_layout.addWidget(model_frame)

        # 新建对话按钮
        new_btn = QPushButton("新建对话")
        new_btn.setStyleSheet(BTN_PRIMARY_QSS())
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._new_session)
        left_layout.addWidget(new_btn)

        # 会话列表标签
        sessions_label = QLabel("历史对话")
        sessions_label.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        sessions_label.setStyleSheet(f"color: {t.get('text')};")
        left_layout.addWidget(sessions_label)

        # 会话列表
        self._session_list = QListWidget()
        self._session_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: {RADIUS['md']};
                color: {t.get('text')};
                margin: 2px 0;
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background-color: {t.get('row_h')};
            }}
            QListWidget::item:selected {{
                background-color: {t.get('accent_bg')};
                color: {t.get('accent')};
                font-weight: 600;
            }}
        """)
        self._session_list.currentRowChanged.connect(self._on_session_selected)
        left_layout.addWidget(self._session_list, 1)

        # 删除按钮
        del_btn = QPushButton("删除选中对话")
        del_btn.setStyleSheet(BTN_DANGER_QSS())
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self._delete_session)
        left_layout.addWidget(del_btn)

        splitter.addWidget(left)

        # ── 右侧：对话区域 ──────────────────────────────────
        right = QWidget()
        right.setStyleSheet(f"background-color: {t.get('bg')};")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(24, 16, 24, 16)
        right_layout.setSpacing(12)

        # 对话标题
        self._chat_title = QLabel("选择或新建一个对话")
        self._chat_title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self._chat_title.setStyleSheet(f"color: {t.get('text_b')};")
        right_layout.addWidget(self._chat_title)

        # 消息显示区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)
        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(0, 0, 0, 0)
        self._messages_layout.setSpacing(16)
        self._messages_layout.addStretch()
        scroll.setWidget(self._messages_container)
        right_layout.addWidget(scroll, 1)

        # ── 底部输入区域 ─────────────────────────────────────
        # 写作辅助快捷按钮
        assist_row = QHBoxLayout()
        assist_row.setSpacing(8)
        assist_label = QLabel("写作辅助:")
        assist_label.setStyleSheet(f"color: {t.get('text_d')}; font-size: 11px;")
        assist_row.addWidget(assist_label)

        for text, mode in [("润色", "polish"), ("翻译", "translate"),
                           ("LaTeX", "latex"), ("摘要", "abstract")]:
            btn = QPushButton(text)
            btn.setStyleSheet(BTN_GHOST_QSS())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self._writing_assist(m))
            assist_row.addWidget(btn)

        assist_row.addStretch()

        # 跨模块按钮
        for text, callback in [("引用文献", self._cite_paper),
                                ("引用试验", self._cite_experiment),
                                ("存为卡片", self._save_as_card)]:
            btn = QPushButton(text)
            btn.setStyleSheet(BTN_GHOST_QSS())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(callback)
            assist_row.addWidget(btn)

        right_layout.addLayout(assist_row)

        # 输入框 + 发送按钮
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('card')};
                border: 1px solid {t.get('border')};
                border-radius: {RADIUS['xl']};
            }}
            QFrame:focus-within {{
                border-color: {t.get('accent')};
            }}
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)

        self._input = QTextEdit()
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {t.get('text')};
                border: none;
                padding: 8px;
                font-size: 13px;
            }}
        """)
        self._input.setPlaceholderText("输入消息... (Enter 发送，Shift+Enter 换行)")
        self._input.setMaximumHeight(80)
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input, 1)

        send_btn = QPushButton("发送")
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {t.get('accent')}, stop:1 {t.get('cyan')});
                color: white;
                border: none;
                border-radius: {RADIUS['lg']};
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {t.get('accent_l')}, stop:1 {t.get('cyan')});
            }}
        """)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)

        right_layout.addWidget(input_frame)

        splitter.addWidget(right)
        splitter.setSizes([260, 740])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def eventFilter(self, obj, event):
        if obj == self._input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._send_message()
                return True
        return super().eventFilter(obj, event)

    def refresh(self):
        self._refresh_sessions()
        self._refresh_models()

    def _refresh_models(self):
        self._ai_router.reload()
        self._model_combo.clear()
        models = self._ai_router.get_all_models()
        for m in models:
            self._model_combo.addItem(f"{m.name} ({m.model_name})", m.id)
        if not models:
            self._model_combo.addItem("未配置模型，请在设置中添加", "")

    def _refresh_sessions(self):
        self._session_list.clear()
        db = get_session()
        try:
            sessions = chat_service.get_sessions(db)
            for s in sessions:
                item = QListWidgetItem(s.title[:30])
                item.setData(Qt.ItemDataRole.UserRole, s.id)
                item.setToolTip(s.title)
                self._session_list.addItem(item)
        finally:
            db.close()

    def _new_session(self):
        db = get_session()
        try:
            model_name = self._model_combo.currentText()
            session = chat_service.create_session(db, title="新对话", model_name=model_name)
            self._current_session_id = session.id
        finally:
            db.close()
        self._refresh_sessions()
        self._session_list.setCurrentRow(0)
        self._clear_messages()
        self._chat_title.setText("新对话")

    def _delete_session(self):
        if not self._current_session_id:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个对话吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        db = get_session()
        try:
            chat_service.delete_session(db, self._current_session_id)
        finally:
            db.close()
        self._current_session_id = None
        self._refresh_sessions()
        self._clear_messages()
        self._chat_title.setText("选择或新建一个对话")

    def _on_session_selected(self, row: int):
        item = self._session_list.item(row)
        if not item:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_session_id = session_id
        self._chat_title.setText(item.text())
        self._load_messages(session_id)

    def _load_messages(self, session_id: str):
        self._clear_messages()
        db = get_session()
        try:
            messages = chat_service.get_messages(db, session_id)
            for msg in messages:
                self._append_message_widget(msg.role, msg.content, msg.thinking_content)
        finally:
            db.close()

    def _clear_messages(self):
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _send_message(self):
        content = self._input.toPlainText().strip()
        if not content:
            return

        if not self._current_session_id:
            self._new_session()

        db = get_session()
        try:
            chat_service.add_message(db, self._current_session_id, "user", content)
            msg_count = chat_service.get_message_count(db, self._current_session_id)
            if msg_count == 1:
                chat_service.update_session_title(db, self._current_session_id, content[:30])
                self._chat_title.setText(content[:30])
        finally:
            db.close()

        self._append_message_widget("user", content)
        self._input.clear()

        db = get_session()
        try:
            messages = chat_service.build_messages_for_ai(db, self._current_session_id)
        finally:
            db.close()

        model_id = self._model_combo.currentData()
        self._start_streaming(messages, model_id)

    def _start_streaming(self, messages: list[dict], model_id: str | None):
        self._current_ai_widget = self._append_message_widget("assistant", "", "")

        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)

        self._worker = _StreamWorker(self._ai_router, messages, model_id=model_id)
        self._worker.thinking_chunk.connect(self._on_thinking_chunk)
        self._worker.content_chunk.connect(self._on_content_chunk)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.error.connect(self._on_stream_error)
        self._worker.start()

    def _on_thinking_chunk(self, text: str):
        if hasattr(self, '_current_ai_widget'):
            thinking_label = self._current_ai_widget._thinking_label
            thinking_label.setVisible(True)
            thinking_label.setText(thinking_label.text() + text)

    def _on_content_chunk(self, text: str):
        if hasattr(self, '_current_ai_widget'):
            content_label = self._current_ai_widget._content_label
            content_label.setText(content_label.text() + text)

    def _on_stream_finished(self, thinking: str, content: str):
        if self._current_session_id:
            db = get_session()
            try:
                chat_service.add_message(db, self._current_session_id, "assistant", content, thinking)
            finally:
                db.close()
        self._refresh_sessions()

    def _on_stream_error(self, error: str):
        if hasattr(self, '_current_ai_widget'):
            self._current_ai_widget._content_label.setText(f"错误: {error}")
            self._current_ai_widget._content_label.setStyleSheet(
                f"color: {self._theme.get('red')}; font-size: 13px;")

    def _append_message_widget(self, role: str, content: str, thinking: str = "") -> QFrame:
        t = self._theme
        is_user = role == "user"

        frame = QFrame()
        if is_user:
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {t.get('accent')};
                    border-radius: 16px;
                    padding: 4px;
                }}
            """)
        else:
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {t.get('card')};
                    border: 1px solid {t.get('border')};
                    border-radius: 16px;
                    padding: 4px;
                }}
            """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # 角色标签
        role_label = QLabel("You" if is_user else "AI")
        role_label.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        role_label.setStyleSheet(f"""
            color: {'rgba(255,255,255,0.8)' if is_user else t.get('accent')};
        """)
        layout.addWidget(role_label)

        # Thinking 内容（默认折叠）
        thinking_label = QLabel(thinking)
        thinking_label.setWordWrap(True)
        thinking_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        thinking_label.setFont(QFont("Inter", 10))
        thinking_label.setStyleSheet(f"""
            color: {t.get('text_d')};
            font-style: italic;
            padding: 8px;
            background-color: {t.get('bg_secondary')};
            border-radius: {RADIUS['md']};
        """)
        thinking_label.setVisible(bool(thinking))
        thinking_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # 点击切换显示/隐藏
        original_thinking = thinking
        thinking_label.mousePressEvent = lambda _: (
            thinking_label.setVisible(False) if thinking_label.text() == original_thinking else None
        )
        layout.addWidget(thinking_label)
        frame._thinking_label = thinking_label

        # 主内容
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        content_label.setFont(QFont("Inter", 13))
        content_label.setStyleSheet(f"""
            color: {'white' if is_user else t.get('text')};
            line-height: 1.5;
        """)
        layout.addWidget(content_label)
        frame._content_label = content_label

        # 插入到 stretch 之前
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, frame)
        return frame

    def _writing_assist(self, mode: str):
        selected = self._input.textCursor().selectedText()
        if not selected:
            selected = self._input.toPlainText().strip()
        if not selected:
            return

        prompts = {
            "polish": f"请润色以下学术文本，保持原意，提升表达质量：\n\n{selected}",
            "translate": f"请将以下文本翻译为学术英语（如果已是英文则翻译为中文）：\n\n{selected}",
            "latex": f"请将以下内容转为LaTeX代码：\n\n{selected}",
            "abstract": f"请根据以下内容生成中英文摘要：\n\n{selected}",
        }
        self._input.setPlainText(prompts.get(mode, selected))
        self._send_message()

    def _cite_paper(self):
        QMessageBox.information(self, "引用文献", "请在文献管理页面选择文献后发送到对话。")

    def _cite_experiment(self):
        QMessageBox.information(self, "引用试验", "请在试验管理页面选择试验后发送到对话。")

    def _save_as_card(self):
        if not self._current_session_id:
            return
        db = get_session()
        try:
            messages = chat_service.get_messages(db, self._current_session_id)
            ai_messages = [m for m in messages if m.role == "assistant"]
            if not ai_messages:
                QMessageBox.information(self, "提示", "没有可保存的AI回复。")
                return
            last = ai_messages[-1]
            from app.services import knowledge_service
            knowledge_service.create_card(
                db, title=last.content[:60], summary=last.content[:500], source_type="deepseek",
            )
            QMessageBox.information(self, "成功", "已保存为知识卡片。")
        finally:
            db.close()
