"""设置对话框：输出目录、输出格式、推理参数、主题。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, cfg: AppConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(560, 520)
        self._cfg = cfg

        form = QFormLayout()

        # 输出目录
        self.out_dir_edit = QLineEdit(cfg.output_dir)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._pick_dir)
        row1 = QHBoxLayout()
        w1 = QWidget(); w1.setLayout(row1)
        row1.setContentsMargins(0, 0, 0, 0)
        row1.addWidget(self.out_dir_edit, 1)
        row1.addWidget(browse)
        form.addRow("输出目录（留空=软件目录/output）:", w1)

        # 输出格式
        self.cb_txt = QCheckBox("txt")
        self.cb_srt = QCheckBox("srt")
        self.cb_vtt = QCheckBox("vtt")
        self.cb_json = QCheckBox("json")
        for cb, code in [(self.cb_txt, "txt"), (self.cb_srt, "srt"),
                         (self.cb_vtt, "vtt"), (self.cb_json, "json")]:
            cb.setChecked(code in cfg.output_formats)
        fmt_row = QHBoxLayout()
        w2 = QWidget(); w2.setLayout(fmt_row)
        fmt_row.setContentsMargins(0, 0, 0, 0)
        for cb in (self.cb_txt, self.cb_srt, self.cb_vtt, self.cb_json):
            fmt_row.addWidget(cb)
        fmt_row.addStretch(1)
        form.addRow("输出格式:", w2)

        # 设备 & 精度
        self.device_combo = QComboBox()
        for label, code in [("自动", "auto"), ("CUDA (GPU)", "cuda"), ("CPU", "cpu")]:
            self.device_combo.addItem(label, code)
        self._select_data(self.device_combo, cfg.device)
        form.addRow("设备:", self.device_combo)

        self.ct_combo = QComboBox()
        for label, code in [
            ("自动", "auto"),
            ("float16 (GPU 最佳)", "float16"),
            ("int8_float16 (省显存)", "int8_float16"),
            ("int8 (CPU 推荐)", "int8"),
        ]:
            self.ct_combo.addItem(label, code)
        self._select_data(self.ct_combo, cfg.compute_type)
        form.addRow("精度 compute_type:", self.ct_combo)

        # beam_size
        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 15)
        self.beam_spin.setValue(cfg.beam_size)
        form.addRow("beam_size (越大越准但越慢):", self.beam_spin)

        # VAD
        self.vad_cb = QCheckBox("启用 VAD 过滤（过滤非人声片段）")
        self.vad_cb.setChecked(cfg.vad_filter)
        form.addRow("VAD:", self.vad_cb)

        # initial_prompt
        self.prompt_edit = QLineEdit(cfg.initial_prompt)
        self.prompt_edit.setPlaceholderText("可为空；可填写专业术语以提升识别准确度")
        form.addRow("初始提示词:", self.prompt_edit)

        # 主题
        self.theme_combo = QComboBox()
        for label, code in [("深色", "dark"), ("浅色", "light"), ("跟随系统", "auto")]:
            self.theme_combo.addItem(label, code)
        self._select_data(self.theme_combo, cfg.theme)
        form.addRow("主题:", self.theme_combo)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addStretch(1)

        note = QLabel("注意：设备/精度/模型的修改在下一次点击“开始转写”时生效。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #888;")
        root.addWidget(note)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    @staticmethod
    def _select_data(combo: QComboBox, data) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", self.out_dir_edit.text() or str(Path.home()))
        if d:
            self.out_dir_edit.setText(d)

    def result_config(self) -> AppConfig:
        fmts = []
        for cb, code in [(self.cb_txt, "txt"), (self.cb_srt, "srt"),
                         (self.cb_vtt, "vtt"), (self.cb_json, "json")]:
            if cb.isChecked():
                fmts.append(code)
        if not fmts:
            fmts = ["txt"]
        return AppConfig(
            output_dir=self.out_dir_edit.text().strip(),
            output_formats=fmts,
            device=self.device_combo.currentData(),
            compute_type=self.ct_combo.currentData(),
            beam_size=self.beam_spin.value(),
            vad_filter=self.vad_cb.isChecked(),
            initial_prompt=self.prompt_edit.text(),
            language=self._cfg.language,
            model_name=self._cfg.model_name,
            theme=self.theme_combo.currentData(),
        )
