"""AI对话页面 — 流式对话 + thinking折叠 + 写作辅助 + 跨模块联动"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QSplitter, QListWidget, QListWidgetItem, QFrame,
    QComboBox, QScrollArea, QDialog, QFormLayout, QDialogButtonBox,
    QLineEdit, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from app.ui.theme import (
    get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, BTN_DANGER_QSS, INPUT_QSS, COMBO_QSS,
)
from app.db import get_session
from app.services import chat_service
from app.ai.router import AIRouter


class _StreamWorker(QThread):
    """AI 流式对话工作线程"""
    thinking_chunk = Signal(str)
    content_chunk = Signal(str)
    finished = Signal(str, str)  # (full_thinking, full_content)
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

        # ── 左侧：会话列表 ──────────────────────────────────
        left = QWidget()
        left.setFixedWidth(240)
        left.setStyleSheet(f"background-color: {t.get('sidebar')};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        # 模型选择
        model_label = QLabel("AI 模型:")
        model_label.setStyleSheet(f"color: {t.get('text_d')};")
        left_layout.addWidget(model_label)

        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet(COMBO_QSS())
        self._refresh_models()
        left_layout.addWidget(self._model_combo)

        # 会话列表
        self._session_list = QListWidget()
        self._session_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                color: {t.get('text')};
                margin: 2px 0;
            }}
            QListWidget::item:hover {{
                background-color: {t.get('sidebar_h')};
            }}
            QListWidget::item:selected {{
                background-color: {t.get('sidebar_s')};
                color: {t.get('accent')};
            }}
        """)
        self._session_list.currentRowChanged.connect(self._on_session_selected)
        left_layout.addWidget(self._session_list, 1)

        # 按钮行
        btn_row = QHBoxLayout()
        new_btn = QPushButton("新对话")
        new_btn.setStyleSheet(BTN_PRIMARY_QSS())
        new_btn.clicked.connect(self._new_session)
        btn_row.addWidget(new_btn)

        del_btn = QPushButton("删除")
        del_btn.setStyleSheet(BTN_DANGER_QSS())
        del_btn.clicked.connect(self._delete_session)
        btn_row.addWidget(del_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        # ── 右侧：对话区域 ──────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(8)

        # 消息显示区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(0, 0, 0, 0)
        self._messages_layout.setSpacing(12)
        self._messages_layout.addStretch()
        scroll.setWidget(self._messages_container)
        right_layout.addWidget(scroll, 1)

        # 快捷操作栏
        actions_row = QHBoxLayout()
        for text, callback in [
            ("📝 润色", lambda: self._writing_assist("polish")),
            ("🌐 翻译", lambda: self._writing_assist("translate")),
            ("📐 LaTeX", lambda: self._writing_assist("latex")),
            ("📋 摘要", lambda: self._writing_assist("abstract")),
        ]:
            btn = QPushButton(text)
            btn.setStyleSheet(BTN_SECONDARY_QSS())
            btn.setFixedHeight(28)
            btn.clicked.connect(callback)
            actions_row.addWidget(btn)
        actions_row.addStretch()

        # 跨模块按钮
        for text, callback in [
            ("📚 引用文献", self._cite_paper),
            ("🧪 引用试验", self._cite_experiment),
            ("💾 存为卡片", self._save_as_card),
        ]:
            btn = QPushButton(text)
            btn.setStyleSheet(BTN_SECONDARY_QSS())
            btn.setFixedHeight(28)
            btn.clicked.connect(callback)
            actions_row.addWidget(btn)
        right_layout.addLayout(actions_row)

        # 输入区域
        input_row = QHBoxLayout()
        self._input = QTextEdit()
        self._input.setStyleSheet(INPUT_QSS())
        self._input.setPlaceholderText("输入消息... (Shift+Enter 换行，Enter 发送)")
        self._input.setMaximumHeight(100)
        self._input.installEventFilter(self)
        input_row.addWidget(self._input, 1)

        send_btn = QPushButton("发送")
        send_btn.setStyleSheet(BTN_PRIMARY_QSS())
        send_btn.setFixedSize(60, 60)
        send_btn.clicked.connect(self._send_message)
        input_row.addWidget(send_btn)
        right_layout.addLayout(input_row)

        splitter.addWidget(right)
        splitter.setSizes([240, 760])
        layout.addWidget(splitter)

    def eventFilter(self, obj, event):
        """Enter 发送，Shift+Enter 换行"""
        if obj == self._input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._send_message()
                return True
        return super().eventFilter(obj, event)

    def refresh(self):
        self._refresh_sessions()
        self._refresh_models()

    def _refresh_models(self):
        """从数据库重新加载模型列表"""
        self._ai_router.reload()  # 重新加载模型配置
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
                item = QListWidgetItem(s.title)
                item.setData(Qt.ItemDataRole.UserRole, s.id)
                self._session_list.addItem(item)
        finally:
            db.close()

    def _new_session(self):
        db = get_session()
        try:
            model_id = self._model_combo.currentData()
            model_name = self._model_combo.currentText()
            session = chat_service.create_session(db, title="新对话", model_name=model_name)
            self._current_session_id = session.id
        finally:
            db.close()
        self._refresh_sessions()
        self._session_list.setCurrentRow(0)
        self._clear_messages()

    def _delete_session(self):
        if not self._current_session_id:
            return
        from PySide6.QtWidgets import QMessageBox
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

    def _on_session_selected(self, row: int):
        item = self._session_list.item(row)
        if not item:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_session_id = session_id
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

        # Save user message
        db = get_session()
        try:
            chat_service.add_message(db, self._current_session_id, "user", content)
            # Auto-title: use first message as title
            msg_count = chat_service.get_message_count(db, self._current_session_id)
            if msg_count == 1:
                chat_service.update_session_title(db, self._current_session_id, content[:30])
        finally:
            db.close()

        self._append_message_widget("user", content)
        self._input.clear()

        # Build messages for AI
        db = get_session()
        try:
            messages = chat_service.build_messages_for_ai(db, self._current_session_id)
        finally:
            db.close()

        model_id = self._model_combo.currentData()
        self._start_streaming(messages, model_id)

    def _start_streaming(self, messages: list[dict], model_id: str | None):
        # Create placeholder for AI response
        self._current_ai_widget = self._append_message_widget("assistant", "", "")

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
        # Save to database
        if self._current_session_id:
            db = get_session()
            try:
                chat_service.add_message(db, self._current_session_id, "assistant", content, thinking)
            finally:
                db.close()
        self._refresh_sessions()

    def _on_stream_error(self, error: str):
        if hasattr(self, '_current_ai_widget'):
            self._current_ai_widget._content_label.setText(f"❌ 错误: {error}")

    def _append_message_widget(self, role: str, content: str, thinking: str = "") -> QFrame:
        t = self._theme
        frame = QFrame()
        is_user = role == "user"
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('accent') if is_user else t.get('card')};
                border-radius: 10px;
                padding: 4px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 角色标签
        role_label = QLabel("👤 你" if is_user else "🤖 AI")
        role_label.setStyleSheet(f"color: {'white' if is_user else t.get('accent')}; font-weight: bold; font-size: 11px;")
        layout.addWidget(role_label)

        # Thinking 内容（默认折叠）
        thinking_label = QLabel(thinking)
        thinking_label.setWordWrap(True)
        thinking_label.setStyleSheet(f"""
            color: {t.get('text_d')};
            font-style: italic;
            font-size: 10px;
            padding: 4px;
            background-color: {t.get('border')};
            border-radius: 4px;
        """)
        thinking_label.setVisible(bool(thinking))
        thinking_label.setCursor(Qt.CursorShape.PointingHandCursor)
        thinking_label.mousePressEvent = lambda _: thinking_label.setVisible(not thinking_label.isVisible())
        layout.addWidget(thinking_label)
        frame._thinking_label = thinking_label

        # 主内容
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        content_label.setStyleSheet(f"color: {'white' if is_user else t.get('text')}; font-size: 12px;")
        layout.addWidget(content_label)
        frame._content_label = content_label

        # 插入到 stretch 之前
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, frame)
        return frame

    def _writing_assist(self, mode: str):
        """写作辅助"""
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
        """引用文献"""
        QMessageBox.information(self, "引用文献", "请在文献管理页面选择文献后发送到对话。\n此功能将在后续版本完善。")

    def _cite_experiment(self):
        """引用试验"""
        QMessageBox.information(self, "引用试验", "请在试验管理页面选择试验后发送到对话。\n此功能将在后续版本完善。")

    def _save_as_card(self):
        """保存最后一条AI回复为知识卡片"""
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
                db,
                title=last.content[:60],
                summary=last.content[:500],
                source_type="deepseek",
            )
            QMessageBox.information(self, "成功", "已保存为知识卡片。")
        finally:
            db.close()
