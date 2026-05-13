#!/usr/bin/env python3
"""把 models/faster-whisper-large-v3/ 打包成 zip，并生成 SHA256SUMS.txt。

用法：
    python scripts/pack_model.py
    python scripts/pack_model.py --src models/faster-whisper-large-v3 --out dist/faster-whisper-large-v3.zip
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def sha256_of(p: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for buf in iter(lambda: f.read(chunk), b""):
            h.update(buf)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "models" / "faster-whisper-large-v3"))
    ap.add_argument("--out", default=str(ROOT / "dist" / "faster-whisper-large-v3.zip"))
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    if not src.is_dir():
        print(f"错误: 源目录不存在: {src}", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"[i] 打包 {src} → {out}")

    files = [p for p in src.rglob("*") if p.is_file()]
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as zf:
        for i, p in enumerate(files, 1):
            # 压缩包内根目录保留为 src.name，和终端用户解压后的结构一致
            arc = Path(src.name) / p.relative_to(src)
            zf.write(p, arcname=str(arc))
            if i % 20 == 0 or i == len(files):
                print(f"  [{i}/{len(files)}] {p.name}")

    sha = sha256_of(out)
    sums = out.parent / "SHA256SUMS.txt"
    sums.write_text(f"{sha}  {out.name}\n", encoding="utf-8")

    print(f"[✓] zip 大小: {out.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"[✓] SHA256: {sha}")
    print(f"[✓] 校验文件: {sums}")
    print(f"\n下一步：把 {out.name} 上传百度网盘，发给终端用户。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
