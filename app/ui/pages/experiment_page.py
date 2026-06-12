"""试验管理页面 — 分栏布局 + 版本化结果 + 参数对比"""

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QListWidget, QListWidgetItem,
    QDialog, QFormLayout, QDialogButtonBox, QFrame, QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.ui.theme import (
    get_theme, BTN_PRIMARY_QSS, BTN_SECONDARY_QSS, BTN_DANGER_QSS,
    INPUT_QSS, COMBO_QSS, TABLE_QSS, TAB_QSS, LIST_WIDGET_QSS, SCROLLBAR_QSS, RADIUS,
)
from app.db import get_session
from app.services import experiment_service


class ExperimentPage(QWidget):
    """试验管理页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._current_exp_id: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        t = self._theme
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 左侧：试验列表 ──────────────────────────────────
        left = QWidget()
        left.setStyleSheet(f"background-color: {t.get('sidebar')};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        # 搜索 + 状态过滤
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 搜索试验...")
        self._search.setStyleSheet(INPUT_QSS())
        self._search.textChanged.connect(self._refresh_list)
        left_layout.addWidget(self._search)

        self._status_filter = QComboBox()
        self._status_filter.addItems(["全部", "planning", "running", "completed", "suspended"])
        self._status_filter.setStyleSheet(COMBO_QSS())
        self._status_filter.currentIndexChanged.connect(self._refresh_list)
        left_layout.addWidget(self._status_filter)

        # 试验列表
        self._exp_list = QListWidget()
        self._exp_list.setStyleSheet(LIST_WIDGET_QSS())
        self._exp_list.currentRowChanged.connect(self._on_exp_selected)
        left_layout.addWidget(self._exp_list, 1)

        # 新建按钮
        add_btn = QPushButton("➕ 新建试验")
        add_btn.setStyleSheet(BTN_PRIMARY_QSS())
        add_btn.clicked.connect(self._add_experiment)
        left_layout.addWidget(add_btn)

        splitter.addWidget(left)

        # ── 右侧：试验详情 ──────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(8)

        # 标题行
        self._title_label = QLabel("选择一个试验")
        self._title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self._title_label.setStyleSheet(f"color: {t.get('text_b')};")
        right_layout.addWidget(self._title_label)

        # Tab 容器
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_QSS())

        # Tab 1: 基本信息
        self._tabs.addTab(self._build_info_tab(), "📋 基本信息")
        # Tab 2: 试验结果
        self._tabs.addTab(self._build_results_tab(), "📊 试验结果")
        # Tab 3: 关联
        self._tabs.addTab(self._build_links_tab(), "🔗 关联")

        right_layout.addWidget(self._tabs, 1)

        splitter.addWidget(right)
        splitter.setSizes([280, 720])
        layout.addWidget(splitter)

    def _build_info_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 状态
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("状态:"))
        self._exp_status = QComboBox()
        self._exp_status.addItems(["planning", "running", "completed", "suspended"])
        self._exp_status.setStyleSheet(COMBO_QSS())
        self._exp_status.currentIndexChanged.connect(self._on_status_changed)
        status_row.addWidget(self._exp_status)
        status_row.addStretch()

        # 操作按钮
        del_btn = QPushButton("🗑️ 删除试验")
        del_btn.setStyleSheet(BTN_DANGER_QSS())
        del_btn.clicked.connect(self._delete_experiment)
        status_row.addWidget(del_btn)
        layout.addLayout(status_row)

        # 背景
        layout.addWidget(QLabel("背景:"))
        self._bg_edit = QTextEdit()
        self._bg_edit.setStyleSheet(INPUT_QSS())
        self._bg_edit.setMaximumHeight(100)
        self._bg_edit.textChanged.connect(self._auto_save_info)
        layout.addWidget(self._bg_edit)

        # 目标
        layout.addWidget(QLabel("目标:"))
        self._obj_edit = QTextEdit()
        self._obj_edit.setStyleSheet(INPUT_QSS())
        self._obj_edit.setMaximumHeight(100)
        self._obj_edit.textChanged.connect(self._auto_save_info)
        layout.addWidget(self._obj_edit)

        # 实验设置
        layout.addWidget(QLabel("实验设置:"))
        self._setup_edit = QTextEdit()
        self._setup_edit.setStyleSheet(INPUT_QSS())
        self._setup_edit.textChanged.connect(self._auto_save_info)
        layout.addWidget(self._setup_edit, 1)

        return page

    def _build_results_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 结果表格
        self._results_table = QTableWidget()
        self._results_table.setColumnCount(5)
        self._results_table.setHorizontalHeaderLabels(["版本", "描述", "参数", "结论", "日期"])
        self._results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._results_table.setStyleSheet(TABLE_QSS())
        self._results_table.doubleClicked.connect(self._edit_result)
        layout.addWidget(self._results_table, 1)

        # 按钮行
        btn_row = QHBoxLayout()
        add_result_btn = QPushButton("➕ 添加结果")
        add_result_btn.setStyleSheet(BTN_PRIMARY_QSS())
        add_result_btn.clicked.connect(self._add_result)
        btn_row.addWidget(add_result_btn)

        del_result_btn = QPushButton("🗑️ 删除选中")
        del_result_btn.setStyleSheet(BTN_DANGER_QSS())
        del_result_btn.clicked.connect(self._delete_result)
        btn_row.addWidget(del_result_btn)

        export_btn = QPushButton("📄 导出 Markdown")
        export_btn.setStyleSheet(BTN_SECONDARY_QSS())
        export_btn.clicked.connect(self._export_markdown)
        btn_row.addWidget(export_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return page

    def _build_links_tab(self) -> QWidget:
        t = self._theme
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)

        info = QLabel("关联的文献和任务将在此显示。")
        info.setStyleSheet(f"color: {t.get('text_d')};")
        layout.addWidget(info)

        layout.addStretch()
        return page

    def refresh(self):
        self._refresh_list()

    def _refresh_list(self):
        self._exp_list.clear()
        db = get_session()
        try:
            search = self._search.text().strip()
            status_map = {0: "", 1: "planning", 2: "running", 3: "completed", 4: "suspended"}
            status = status_map.get(self._status_filter.currentIndex(), "")
            exps = experiment_service.get_experiments(db, search, status)
            for exp in exps:
                item = QListWidgetItem(f"{exp.title}  [{exp.status}]")
                item.setData(Qt.ItemDataRole.UserRole, exp.id)
                self._exp_list.addItem(item)
        finally:
            db.close()

    def _on_exp_selected(self, row: int):
        item = self._exp_list.item(row)
        if not item:
            return
        exp_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_exp_id = exp_id
        self._load_experiment(exp_id)

    def _load_experiment(self, exp_id: str):
        db = get_session()
        try:
            exp = experiment_service.get_experiment(db, exp_id)
            if not exp:
                return
            self._title_label.setText(exp.title)
            self._exp_status.setCurrentText(exp.status)
            self._bg_edit.blockSignals(True)
            self._obj_edit.blockSignals(True)
            self._setup_edit.blockSignals(True)
            self._bg_edit.setText(exp.background)
            self._obj_edit.setText(exp.objective)
            self._setup_edit.setText(exp.setup)
            self._bg_edit.blockSignals(False)
            self._obj_edit.blockSignals(False)
            self._setup_edit.blockSignals(False)

            # Load results
            results = experiment_service.get_results(db, exp_id)
            self._results_table.setRowCount(len(results))
            for i, r in enumerate(results):
                self._results_table.setItem(i, 0, QTableWidgetItem(f"v{r.version}"))
                self._results_table.setItem(i, 1, QTableWidgetItem(r.description[:50]))
                params = json.loads(r.parameters) if r.parameters else {}
                params_str = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3])
                self._results_table.setItem(i, 2, QTableWidgetItem(params_str))
                self._results_table.setItem(i, 3, QTableWidgetItem(r.conclusion[:50]))
                self._results_table.setItem(i, 4, QTableWidgetItem(r.created_at.strftime("%Y-%m-%d")))
                self._results_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, r.id)
        finally:
            db.close()

    def _auto_save_info(self):
        if not self._current_exp_id:
            return
        db = get_session()
        try:
            experiment_service.update_experiment(
                db, self._current_exp_id,
                background=self._bg_edit.toPlainText(),
                objective=self._obj_edit.toPlainText(),
                setup=self._setup_edit.toPlainText(),
            )
        finally:
            db.close()

    def _on_status_changed(self, index: int):
        if not self._current_exp_id:
            return
        status = self._exp_status.currentText()
        db = get_session()
        try:
            experiment_service.update_experiment(db, self._current_exp_id, status=status)
        finally:
            db.close()
        self._refresh_list()

    def _add_experiment(self):
        dialog = AddExperimentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            db = get_session()
            try:
                experiment_service.create_experiment(db, **data)
            finally:
                db.close()
            self._refresh_list()

    def _delete_experiment(self):
        if not self._current_exp_id:
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此试验及其所有结果吗？")
        if reply == QMessageBox.StandardButton.Yes:
            db = get_session()
            try:
                experiment_service.delete_experiment(db, self._current_exp_id)
            finally:
                db.close()
            self._current_exp_id = None
            self._title_label.setText("选择一个试验")
            self._refresh_list()

    def _add_result(self):
        if not self._current_exp_id:
            return
        dialog = AddResultDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            db = get_session()
            try:
                experiment_service.add_result(db, self._current_exp_id, **data)
            finally:
                db.close()
            self._load_experiment(self._current_exp_id)

    def _delete_result(self):
        row = self._results_table.currentRow()
        if row < 0:
            return
        result_id = self._results_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        db = get_session()
        try:
            experiment_service.delete_result(db, result_id)
        finally:
            db.close()
        if self._current_exp_id:
            self._load_experiment(self._current_exp_id)

    def _edit_result(self, index):
        row = index.row()
        result_id = self._results_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        # TODO: open edit dialog
        pass

    def _export_markdown(self):
        if not self._current_exp_id:
            return
        db = get_session()
        try:
            md = experiment_service.export_experiment_markdown(db, self._current_exp_id)
        finally:
            db.close()
        if md:
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(self, "导出 Markdown", "", "Markdown (*.md)")
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(md)


class AddExperimentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建试验")
        self.setMinimumWidth(400)
        t = get_theme()
        self.setStyleSheet(f"background-color: {t.get('bg')}; color: {t.get('text')};")

        layout = QFormLayout(self)
        self._title = QLineEdit()
        self._title.setStyleSheet(INPUT_QSS())
        layout.addRow("试验名称:", self._title)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {"title": self._title.text().strip()}


class AddResultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加试验结果")
        self.setMinimumWidth(500)
        t = get_theme()
        self.setStyleSheet(f"background-color: {t.get('bg')}; color: {t.get('text')};")

        layout = QFormLayout(self)

        self._desc = QLineEdit()
        self._desc.setStyleSheet(INPUT_QSS())
        layout.addRow("描述:", self._desc)

        self._params = QTextEdit()
        self._params.setStyleSheet(INPUT_QSS())
        self._params.setPlaceholderText('JSON格式，如: {"lr": 0.001, "epochs": 100}')
        self._params.setMaximumHeight(80)
        layout.addRow("参数 (JSON):", self._params)

        self._code = QTextEdit()
        self._code.setStyleSheet(INPUT_QSS())
        self._code.setPlaceholderText("关键代码片段...")
        self._code.setMaximumHeight(100)
        layout.addRow("代码片段:", self._code)

        self._result = QTextEdit()
        self._result.setStyleSheet(INPUT_QSS())
        self._result.setPlaceholderText("结果数据...")
        self._result.setMaximumHeight(80)
        layout.addRow("结果数据:", self._result)

        self._conclusion = QLineEdit()
        self._conclusion.setStyleSheet(INPUT_QSS())
        layout.addRow("结论:", self._conclusion)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        params = {}
        try:
            params = json.loads(self._params.toPlainText() or "{}")
        except json.JSONDecodeError:
            pass

        code_snippets = []
        code_text = self._code.toPlainText().strip()
        if code_text:
            code_snippets = [{"file": "snippet", "code": code_text, "diff": ""}]

        return {
            "description": self._desc.text().strip(),
            "parameters": params,
            "code_snippets": code_snippets,
            "result_data": self._result.toPlainText().strip(),
            "conclusion": self._conclusion.text().strip(),
        }
