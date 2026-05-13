"""WhisperDesk 主窗口。"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app import config, paths
from app.exporters import export_all
from app.settings_dialog import SettingsDialog
from app.transcribe_worker import TranscribeWorker, detect_device_and_compute_type

log = logging.getLogger(__name__)

SUPPORTED_EXTS = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg", ".aac", ".webm", ".opus"}


class DropArea(QFrame):
    """拖放区，点击 / 拖入文件。"""

    def __init__(self, on_file_selected, parent=None):
        super().__init__(parent)
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        self._on = on_file_selected

        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)

        title = QLabel("🎙  将音频文件拖到此处，或点击选择")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("DropTitle")

        hint = QLabel("支持 mp3 / wav / m4a / mp4 / flac / ogg")
        hint.setAlignment(Qt.AlignCenter)
        hint.setObjectName("DropHint")

        self._current = QLabel("")
        self._current.setAlignment(Qt.AlignCenter)
        self._current.setObjectName("DropCurrent")
        self._current.setWordWrap(True)

        v.addWidget(title)
        v.addWidget(hint)
        v.addSpacing(8)
        v.addWidget(self._current)

    def set_current(self, path: Optional[Path]):
        self._current.setText(f"已选择：{path}" if path else "")

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            fn, _ = QFileDialog.getOpenFileName(
                self,
                "选择音频文件",
                "",
                "音频文件 (*.mp3 *.wav *.m4a *.mp4 *.flac *.ogg *.aac *.webm *.opus);;所有文件 (*)",
            )
            if fn:
                self._on(Path(fn))
        super().mousePressEvent(ev)

    def dragEnterEvent(self, ev: QDragEnterEvent):
        md: QMimeData = ev.mimeData()
        if md.hasUrls() and any(self._is_audio(u) for u in md.urls()):
            self.setProperty("dragging", True)
            self.style().unpolish(self); self.style().polish(self)
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dragLeaveEvent(self, ev):
        self.setProperty("dragging", False)
        self.style().unpolish(self); self.style().polish(self)
        super().dragLeaveEvent(ev)

    def dropEvent(self, ev: QDropEvent):
        self.setProperty("dragging", False)
        self.style().unpolish(self); self.style().polish(self)
        for u in ev.mimeData().urls():
            if self._is_audio(u):
                self._on(Path(u.toLocalFile()))
                ev.acceptProposedAction()
                return
        ev.ignore()

    @staticmethod
    def _is_audio(u: QUrl) -> bool:
        p = Path(u.toLocalFile())
        return p.suffix.lower() in SUPPORTED_EXTS


LANGUAGES = [
    ("自动检测", "auto"),
    ("英语 English", "en"),
    ("中文", "zh"),
    ("日语", "ja"),
    ("韩语", "ko"),
    ("法语", "fr"),
    ("德语", "de"),
    ("西班牙语", "es"),
    ("俄语", "ru"),
]

DEVICES = [("自动", "auto"), ("CUDA (GPU)", "cuda"), ("CPU", "cpu")]


class MainWindow(QMainWindow):
    def __init__(self, cfg: config.AppConfig):
        super().__init__()
        self.cfg = cfg
        self._audio: Optional[Path] = None
        self._worker: Optional[TranscribeWorker] = None
        self._segments: list[dict] = []

        self.setWindowTitle("WhisperDesk — 本地语音转文字")
        self.resize(880, 640)

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        self.drop = DropArea(self._on_file_selected)
        root.addWidget(self.drop)

        # 选项行
        row = QHBoxLayout()
        row.setSpacing(10)
        self.lang = QComboBox()
        for label, code in LANGUAGES:
            self.lang.addItem(label, code)
        self._select_by_data(self.lang, cfg.language)

        self.model_combo = QComboBox()
        self._refresh_models()

        self.device_combo = QComboBox()
        for label, code in DEVICES:
            self.device_combo.addItem(label, code)
        self._select_by_data(self.device_combo, cfg.device)

        row.addWidget(QLabel("语言:"))
        row.addWidget(self.lang, 1)
        row.addWidget(QLabel("模型:"))
        row.addWidget(self.model_combo, 2)
        row.addWidget(QLabel("设备:"))
        row.addWidget(self.device_combo, 1)
        root.addLayout(row)

        # 结果区
        result_bar = QHBoxLayout()
        result_bar.addWidget(QLabel("转写结果"))
        result_bar.addStretch(1)
        self.copy_btn = QPushButton("复制")
        self.save_btn = QPushButton("保存…")
        self.copy_btn.clicked.connect(self._copy_result)
        self.save_btn.clicked.connect(self._save_result_as)
        result_bar.addWidget(self.copy_btn)
        result_bar.addWidget(self.save_btn)
        root.addLayout(result_bar)

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setObjectName("Result")
        self.result.setPlaceholderText("转写后的文本会显示在这里…")
        root.addWidget(self.result, 1)

        # 进度
        pbox = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.time_label = QLabel("00:00 / 00:00")
        pbox.addWidget(self.progress, 1)
        pbox.addWidget(self.time_label)
        root.addLayout(pbox)

        # 按钮
        btns = QHBoxLayout()
        self.start_btn = QPushButton("开始转写")
        self.start_btn.setObjectName("Primary")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.settings_btn = QPushButton("设置")
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn.clicked.connect(self._cancel)
        self.settings_btn.clicked.connect(self._open_settings)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.cancel_btn)
        btns.addStretch(1)
        btns.addWidget(self.settings_btn)
        root.addLayout(btns)

    # ---------- helpers ----------

    @staticmethod
    def _select_by_data(combo: QComboBox, data) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return

    def _refresh_models(self) -> None:
        """扫描 models/ 下的模型，兜底使用 resolve_model_dir 同款探测逻辑。"""
        self.model_combo.clear()
        root = paths.models_root()
        found: list[tuple[str, str]] = []  # (display_name, data=dir_name_key)

        if root.exists():
            seen: set[str] = set()
            # 一级：models/<name>/model.bin
            for child in root.iterdir():
                if child.is_dir() and (child / "model.bin").exists():
                    found.append((child.name, child.name))
                    seen.add(child.name)
            # 二级兜底：models/<outer>/<inner>/model.bin  （嵌套一层）
            for child in root.iterdir():
                if not child.is_dir() or child.name in seen:
                    continue
                try:
                    for gc in child.iterdir():
                        if gc.is_dir() and (gc / "model.bin").exists():
                            # 下拉框显示外层名，因为 resolve_model_dir 会用外层名探测
                            found.append((f"{child.name} (嵌套)", child.name))
                            seen.add(child.name)
                            break
                except OSError:
                    continue

        if not found:
            self.model_combo.addItem("(未检测到模型)", "")
        else:
            for display, data in sorted(found):
                self.model_combo.addItem(display, data)
            self._select_by_data(self.model_combo, self.cfg.model_name)

    # ---------- file handling ----------

    def _on_file_selected(self, p: Path):
        if p.suffix.lower() not in SUPPORTED_EXTS:
            QMessageBox.warning(self, "不支持的文件", f"不支持的扩展名：{p.suffix}")
            return
        self._audio = p
        self.drop.set_current(p)

    # ---------- transcribe lifecycle ----------

    def _start(self):
        if self._worker and self._worker.isRunning():
            return
        if not self._audio:
            QMessageBox.information(self, "提示", "请先选择或拖入一个音频文件。")
            return

        model_dir = paths.resolve_model_dir(self.model_combo.currentData() or "faster-whisper-large-v3")
        if not model_dir:
            self._prompt_model_missing()
            return

        prefer = self.device_combo.currentData() or "auto"
        device, compute_type = detect_device_and_compute_type(
            prefer=prefer, compute_type=self.cfg.compute_type
        )

        self._segments = []
        self.result.clear()
        self.progress.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.settings_btn.setEnabled(False)

        lang = self.lang.currentData()
        self._worker = TranscribeWorker(
            audio_path=str(self._audio),
            model_dir=str(model_dir),
            device=device,
            compute_type=compute_type,
            language=lang,
            beam_size=self.cfg.beam_size,
            vad_filter=self.cfg.vad_filter,
            initial_prompt=self.cfg.initial_prompt,
        )
        self._worker.segment.connect(self._on_segment)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.result.append("\n[已请求取消，正在停止…]")

    # ---------- worker signal handlers ----------

    def _on_segment(self, start: float, end: float, text: str):
        self._segments.append({"start": start, "end": end, "text": text})
        cursor = self.result.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(f"[{self._fmt(start)} → {self._fmt(end)}] {text.strip()}\n")
        self.result.setTextCursor(cursor)
        self.result.ensureCursorVisible()

    def _on_progress(self, processed: float, total: float):
        if total <= 0:
            return
        pct = max(0.0, min(1.0, processed / total))
        self.progress.setValue(int(pct * 1000))
        self.time_label.setText(f"{self._fmt(processed)} / {self._fmt(total)}")

    def _on_finished(self, segments: list, info: dict):
        self._reset_buttons()
        self.progress.setValue(1000)

        out_dir = Path(self.cfg.output_dir) if self.cfg.output_dir else paths.output_dir()
        try:
            written = export_all(
                segments, info, self._audio, out_dir, self.cfg.output_formats
            )
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"转写完成但写文件失败：{e}")
            return
        file_list = "\n".join(str(p) for p in written)
        QMessageBox.information(
            self,
            "转写完成",
            f"语言: {info.get('language','?')}  时长: {self._fmt(info.get('duration', 0))}\n"
            f"已保存到:\n{file_list}",
        )

    def _on_failed(self, msg: str):
        self._reset_buttons()
        log.error("转写失败: %s", msg)
        QMessageBox.critical(self, "转写失败", msg)

    def _reset_buttons(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.settings_btn.setEnabled(True)

    # ---------- misc ----------

    @staticmethod
    def _fmt(t: float) -> str:
        try:
            t = float(t)
        except Exception:
            t = 0.0
        h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _copy_result(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.result.toPlainText())

    def _save_result_as(self):
        if not self.result.toPlainText():
            return
        fn, _ = QFileDialog.getSaveFileName(
            self, "保存转写结果", "transcript.txt",
            "纯文本 (*.txt);;字幕 (*.srt);;所有文件 (*)"
        )
        if fn:
            Path(fn).write_text(self.result.toPlainText(), encoding="utf-8")

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec():
            self.cfg = dlg.result_config()
            config.save_config(self.cfg)
            # 主题切换立即生效
            try:
                import qdarktheme
                qdarktheme.setup_theme(
                    self.cfg.theme if self.cfg.theme in ("dark", "light", "auto") else "dark"
                )
            except Exception:
                pass
            self._refresh_models()

    def _prompt_model_missing(self):
        expected = paths.models_root() / "faster-whisper-large-v3"
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("未找到模型文件")
        box.setText("软件没有找到 Whisper 模型。")
        box.setInformativeText(
            f"请把解压得到的 faster-whisper-large-v3 整个文件夹放到：\n\n"
            f"{paths.models_root()}\n\n"
            f"最终文件应存在：\n{expected / 'model.bin'}"
        )
        open_btn = box.addButton("打开 models 目录", QMessageBox.ActionRole)
        retry_btn = box.addButton("我已放好，重新检测", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is open_btn:
            self._open_folder(paths.models_root())
        elif clicked is retry_btn:
            self._refresh_models()
            if paths.resolve_model_dir():
                QMessageBox.information(self, "已找到模型", "模型检测成功，可以开始转写了。")

    @staticmethod
    def _open_folder(p: Path):
        p.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(p))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{p}"')
            else:
                os.system(f'xdg-open "{p}"')
        except Exception as e:
            log.warning("打开目录失败: %s", e)
