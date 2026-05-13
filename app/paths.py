"""运行时路径探测与模型目录智能解析。

在 PyInstaller 打包后 `sys.frozen=True`，`sys.executable` 指向 exe，
所以 `app_root()` 取其所在目录；开发时回退到项目根目录。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def app_root() -> Path:
    """应用根目录：打包后是 exe 所在目录；开发时是项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def models_root() -> Path:
    return app_root() / "models"


def output_dir() -> Path:
    d = app_root() / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ffmpeg_exe() -> Path:
    return app_root() / "ffmpeg" / "ffmpeg.exe"


def ensure_ffmpeg_on_path() -> None:
    """把内置 ffmpeg 目录加到当前进程 PATH 最前面。

    faster-whisper 内部通过 subprocess 调 ffmpeg 解码音频，
    必须保证 `ffmpeg` 可在 PATH 中被找到。
    """
    exe = ffmpeg_exe()
    if exe.exists():
        os.environ["PATH"] = str(exe.parent) + os.pathsep + os.environ.get("PATH", "")


# ---------- 模型目录智能解析 ----------

# faster-whisper 模型目录必需文件
_REQUIRED = ("model.bin", "tokenizer.json", "config.json")

# 常见别名（用户可能改过文件夹名）
_ALIASES = (
    "faster-whisper-large-v3",
    "large-v3",
    "whisper-large-v3",
    "faster-whisper-large-v3-ct2",
    "Systran--faster-whisper-large-v3",
)


def _looks_like_model_dir(p: Path) -> bool:
    try:
        return p.is_dir() and all((p / f).exists() for f in _REQUIRED)
    except OSError:
        return False


def resolve_model_dir(preferred_name: str = "faster-whisper-large-v3") -> Optional[Path]:
    """按 4 级容错探测模型目录，命中即返回绝对路径；全部落空返回 None。

    探测顺序：
      1. models/<preferred_name>/
      2. models/<preferred_name>/<preferred_name>/   (用户嵌套一层)
      3. models/<常见别名>/
      4. models/ 下任意子目录（含再向下一层）中匹配必需文件集
    """
    root = models_root()
    if not root.exists():
        return None

    # 1 & 2
    p1 = root / preferred_name
    if _looks_like_model_dir(p1):
        return p1.resolve()
    p2 = p1 / preferred_name
    if _looks_like_model_dir(p2):
        return p2.resolve()

    # 3
    for alias in _ALIASES:
        if alias == preferred_name:
            continue
        p = root / alias
        if _looks_like_model_dir(p):
            return p.resolve()

    # 4 兜底：遍历 models/ 子目录与孙子目录
    try:
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if _looks_like_model_dir(child):
                return child.resolve()
            try:
                for gc in child.iterdir():
                    if _looks_like_model_dir(gc):
                        return gc.resolve()
            except OSError:
                continue
    except OSError:
        return None

    return None
