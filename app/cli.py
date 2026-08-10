"""Console entry point for the optional PySide6 desktop application."""

from __future__ import annotations

import importlib.util
import sys


def main() -> int:
    """Start the legacy PySide6 desktop UI with an actionable dependency error."""
    if importlib.util.find_spec("PySide6") is None:
        print(
            "The 'nexus' command requires the optional desktop dependencies.\n"
            "Install them with: pip install -e \".[desktop]\"",
            file=sys.stderr,
        )
        return 2

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from app.db import init_db
    from app.ui.main_window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("AI Nexus Assistant")
    application.setStyle("Fusion")
    application.setFont(QFont("Microsoft YaHei", 10))

    init_db()
    window = MainWindow()
    window.show()
    return application.exec()
