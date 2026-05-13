"""应用配置读写。持久化到 %APPDATA%/WhisperDesk/config.json（Linux 下 ~/.config/WhisperDesk/）。"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List


def user_config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    d = Path(base) / "WhisperDesk"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return user_config_dir() / "config.json"


def log_path() -> Path:
    return user_config_dir() / "whisperdesk.log"


@dataclass
class AppConfig:
    # 输出
    output_dir: str = ""                         # 空则使用 app_root()/output
    output_formats: List[str] = field(default_factory=lambda: ["txt", "srt"])

    # 推理
    device: str = "auto"                         # auto | cuda | cpu
    compute_type: str = "auto"                   # auto -> 根据 device 选 float16/int8
    beam_size: int = 5
    vad_filter: bool = True
    initial_prompt: str = ""
    language: str = "auto"                       # auto | en | zh | ...
    model_name: str = "faster-whisper-large-v3"

    # UI
    theme: str = "dark"                          # dark | light | auto

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "AppConfig":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


def load_config() -> AppConfig:
    p = config_path()
    if not p.exists():
        return AppConfig()
    try:
        return AppConfig.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        # 配置损坏时回退默认，不影响启动
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    config_path().write_text(cfg.to_json(), encoding="utf-8")


# ---------- logging ----------

def setup_logging() -> None:
    import logging
    from logging.handlers import RotatingFileHandler

    root = logging.getLogger()
    if root.handlers:
        return  # 已初始化
    root.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = RotatingFileHandler(log_path(), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)
