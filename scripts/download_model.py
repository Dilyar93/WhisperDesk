#!/usr/bin/env python3
"""从 HuggingFace 下载 faster-whisper large-v3 模型到本地 models/ 目录。

用法：
    python scripts/download_model.py
    python scripts/download_model.py --repo Systran/faster-whisper-large-v3 --out models/faster-whisper-large-v3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_REPO = "Systran/faster-whisper-large-v3"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "models" / "faster-whisper-large-v3"
REQUIRED = ("model.bin", "tokenizer.json", "config.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO, help="HuggingFace repo id")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="目标目录")
    ap.add_argument("--hf-mirror", default=None, help="可选 HF 镜像，例如 https://hf-mirror.com")
    args = ap.parse_args()

    if args.hf_mirror:
        import os
        os.environ["HF_ENDPOINT"] = args.hf_mirror
        print(f"[i] 使用 HF 镜像: {args.hf_mirror}")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("错误: 未安装 huggingface_hub，请先 `pip install huggingface_hub`", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[i] 下载 {args.repo} → {out}")

    snapshot_download(
        repo_id=args.repo,
        local_dir=str(out),
        local_dir_use_symlinks=False,
        # 排除无关文件，省带宽
        ignore_patterns=["*.md", "*.gitattributes", ".gitignore"],
    )

    # 校验
    missing = [f for f in REQUIRED if not (out / f).exists()]
    if missing:
        print(f"错误: 下载后缺少必需文件: {missing}", file=sys.stderr)
        return 2

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"[✓] 下载完成。总大小: {total / 1024 / 1024:.1f} MB")
    print(f"[✓] 路径: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
