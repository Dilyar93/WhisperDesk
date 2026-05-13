"""WhisperDesk 入口：创建 QApplication、应用主题与 QSS、启动主窗口。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import config, paths
from app.main_window import MainWindow

log = logging.getLogger(__name__)


def _load_qss() -> str:
    qss_path = Path(__file__).resolve().parent / "resources" / "style.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


def _apply_theme(app: QApplication, theme: str) -> None:
    try:
        import qdarktheme
        qdarktheme.setup_theme(theme if theme in ("dark", "light", "auto") else "dark")
    except Exception as e:
        log.warning("qdarktheme 应用失败，回退默认主题: %s", e)
    extra = _load_qss()
    if extra:
        app.setStyleSheet(app.styleSheet() + "\n" + extra)


def main() -> int:
    config.setup_logging()
    paths.ensure_ffmpeg_on_path()
    cfg = config.load_config()

    # 高 DPI 支持由 Qt 6 默认处理
    app = QApplication(sys.argv)
    app.setApplicationName("WhisperDesk")
    app.setOrganizationName("WhisperDesk")

    icon_path = Path(__file__).resolve().parent / "resources" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    _apply_theme(app, cfg.theme)

    win = MainWindow(cfg)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
