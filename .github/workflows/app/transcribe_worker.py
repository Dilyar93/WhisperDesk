"""faster-whisper 推理 Worker，运行在 QThread 中，通过信号把进度/文本推回 GUI。"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)


def detect_device_and_compute_type(prefer: str = "auto", compute_type: str = "auto") -> tuple[str, str]:
    """根据用户偏好 + 硬件能力决定实际使用的 device / compute_type。

    prefer: auto | cuda | cpu
    compute_type: auto | float16 | int8_float16 | int8
    """
    has_cuda = False
    try:
        import ctranslate2
        has_cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception as e:
        log.warning("ctranslate2 CUDA 检测失败: %s", e)

    if prefer == "cpu" or (prefer == "auto" and not has_cuda):
        device = "cpu"
    else:
        device = "cuda" if has_cuda else "cpu"

    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    log.info("device=%s compute_type=%s (cuda_available=%s)", device, compute_type, has_cuda)
    return device, compute_type


class TranscribeWorker(QThread):
    # processed_seconds, total_seconds
    progress = Signal(float, float)
    # start, end, text
    segment = Signal(float, float, str)
    # all_segments (list[dict]), info (dict)
    finished_ok = Signal(list, dict)
    # human readable error
    failed = Signal(str)

    def __init__(
        self,
        audio_path: str,
        model_dir: str,
        device: str,
        compute_type: str,
        language: Optional[str],
        beam_size: int,
        vad_filter: bool,
        initial_prompt: Optional[str],
        parent=None,
    ):
        super().__init__(parent)
        self.audio_path = audio_path
        self.model_dir = model_dir
        self.device = device
        self.compute_type = compute_type
        self.language = None if (language in (None, "", "auto")) else language
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.initial_prompt = initial_prompt or None
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: C901
        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            self.failed.emit(f"faster-whisper 未正确安装: {e}")
            return

        try:
            log.info("加载模型 %s (device=%s, compute_type=%s)", self.model_dir, self.device, self.compute_type)
            model = WhisperModel(
                self.model_dir,
                device=self.device,
                compute_type=self.compute_type,
                local_files_only=True,
            )
        except Exception as e:
            msg = str(e)
            if "out of memory" in msg.lower() or "cuda" in msg.lower() and "memory" in msg.lower():
                self.failed.emit(f"GPU 显存不足，建议在设置中把精度改为 int8_float16 或切换到 CPU。\n原始错误: {e}")
            else:
                self.failed.emit(f"模型加载失败: {e}")
            return

        try:
            segments_iter, info = model.transcribe(
                self.audio_path,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                initial_prompt=self.initial_prompt,
                word_timestamps=False,
            )
        except Exception as e:
            self.failed.emit(f"无法读取音频或启动转写: {e}")
            return

        total = float(getattr(info, "duration", 0.0) or 0.0)
        collected: list[dict] = []
        try:
            for seg in segments_iter:
                if self._cancel:
                    log.info("用户取消转写")
                    return
                item = {"start": float(seg.start), "end": float(seg.end), "text": seg.text}
                collected.append(item)
                self.segment.emit(item["start"], item["end"], item["text"])
                self.progress.emit(item["end"], total)
        except Exception as e:
            self.failed.emit(f"转写过程中出错: {e}")
            return

        self.finished_ok.emit(
            collected,
            {
                "language": getattr(info, "language", ""),
                "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
                "duration": total,
            },
        )
