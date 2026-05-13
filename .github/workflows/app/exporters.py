"""把转写 segments 导出为 txt / srt / vtt / json。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Mapping


Segment = Mapping[str, object]  # {"start": float, "end": float, "text": str}


def _format_ts(t: float, sep: str = ",") -> str:
    t = max(0.0, float(t))
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:  # 四舍五入进位
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_txt(segments: Iterable[Segment]) -> str:
    return "\n".join(str(seg["text"]).strip() for seg in segments) + "\n"


def to_srt(segments: Iterable[Segment]) -> str:
    out: List[str] = []
    for i, seg in enumerate(segments, 1):
        out.append(f"{i}")
        out.append(f"{_format_ts(float(seg['start']), ',')} --> {_format_ts(float(seg['end']), ',')}")
        out.append(str(seg["text"]).strip())
        out.append("")
    return "\n".join(out)


def to_vtt(segments: Iterable[Segment]) -> str:
    out: List[str] = ["WEBVTT", ""]
    for seg in segments:
        out.append(f"{_format_ts(float(seg['start']), '.')} --> {_format_ts(float(seg['end']), '.')}")
        out.append(str(seg["text"]).strip())
        out.append("")
    return "\n".join(out)


def to_json(segments: Iterable[Segment], info: Mapping[str, object] | None = None) -> str:
    return json.dumps(
        {"info": dict(info or {}), "segments": [dict(s) for s in segments]},
        ensure_ascii=False,
        indent=2,
    )


def unique_path(target: Path) -> Path:
    """若 target 已存在则追加 -2、-3 ... 直到唯一。"""
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    parent = target.parent
    i = 2
    while True:
        cand = parent / f"{stem}-{i}{suffix}"
        if not cand.exists():
            return cand
        i += 1


def export_all(
    segments: List[Segment],
    info: Mapping[str, object],
    audio_path: Path,
    out_dir: Path,
    formats: Iterable[str],
) -> List[Path]:
    """按勾选格式把结果写到 out_dir，返回写入文件路径列表。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(audio_path).stem
    written: List[Path] = []

    writers = {
        "txt": (".txt", lambda: to_txt(segments)),
        "srt": (".srt", lambda: to_srt(segments)),
        "vtt": (".vtt", lambda: to_vtt(segments)),
        "json": (".json", lambda: to_json(segments, info)),
    }
    for fmt in formats:
        fmt = fmt.lower()
        if fmt not in writers:
            continue
        ext, maker = writers[fmt]
        p = unique_path(out_dir / f"{stem}{ext}")
        p.write_text(maker(), encoding="utf-8")
        written.append(p)
    return written
